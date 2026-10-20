"""Show each Concerted Abduction stage in a terminal.

Live mode uses the configured components on a generated synthetic data sample.
Replay mode displays saved LM outputs and reruns Dempster's rule without API calls.

    uv run python scripts/demo.py
    uv run python scripts/demo.py --pause
    uv run python scripts/demo.py --scenario-id sample_high_02
    uv run python scripts/demo.py --replay experiments/runs/<run>/<scenario>
"""

import argparse
import json
import random
from collections.abc import Iterable, Sequence
from pathlib import Path
from tempfile import mkdtemp

from pydantic import BaseModel
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from concerted_abduction.bpa import BpaRegistry
from concerted_abduction.combiners import CombinerRegistry
from concerted_abduction.combiners.dempster import DempsterCombination
from concerted_abduction.focal_set import FocalSetRegistry
from concerted_abduction.fod import FodExtractorRegistry
from concerted_abduction.types import (
    BpaOutput,
    DataSample,
    DataSet,
    FocalSetOutput,
    FodOutput,
)
from concerted_abduction.utils.run_utils import latest_run_dir, save_run_metadata
from config.settings import ComponentConfig, ConcertedAbductionSettings, ENVSettings

console = Console(highlight=False, markup=False)


def load_sample(
    dataset_path: Path, scenario_id: str | None = None, *, random_sample: bool = True
) -> DataSample:
    dataset = DataSet.model_validate_json(dataset_path.read_text(encoding="utf-8"))
    if not dataset.samples:
        raise ValueError(f"Dataset contains no samples: {dataset_path}")
    if scenario_id is not None:
        sample = dataset.get_sample_by_id(scenario_id)
    else:
        sample = random.choice(dataset.samples) if random_sample else dataset.samples[0]
    if sample is None:
        raise ValueError(f"Scenario {scenario_id!r} not found in {dataset_path}")
    if not sample.outputs:
        raise ValueError(f"Scenario {sample.scenario_id!r} contains no source responses")
    return sample


def subset(labels: Iterable[str]) -> str:
    return "{" + ", ".join(sorted(labels)) + "}"


def table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    """Render wrapped tables with literal source text and aligned numeric columns."""
    output = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=True)
    for header in headers:
        numeric = header in {"Mass", "Combined mass"}
        output.add_column(
            header, justify="right" if numeric else "left",
            style="bold green" if numeric else None, overflow="fold",
        )
    for row in rows:
        output.add_row(*(Text(cell) for cell in row))
    console.print(output)


def stage(title: str, inputs: str, pause: bool) -> None:
    if pause:
        input("\nPress Enter to continue...")
    console.print()
    console.rule(Text(title, style="bold cyan"), align="left")
    console.print(Text(f"Input: {inputs}"))


def save(directory: Path, filename: str, result: BaseModel) -> None:
    (directory / filename).write_text(result.model_dump_json(indent=2), encoding="utf-8")


def configured[T](component: type[T], cfg: ComponentConfig) -> T:
    factory = getattr(component, "from_config", None)
    if not callable(factory):
        raise TypeError(f"{component.__name__} must provide from_config()")
    result = factory(cfg)
    if not isinstance(result, component):
        raise TypeError(f"{component.__name__}.from_config() returned an unexpected type")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--replay", type=Path, metavar="SCENARIO_DIR",
        help="Read frame.json, focal_sets.json, and bpa.json; make no LM calls.",
    )
    mode.add_argument(
        "--dataset", type=Path, metavar="JSON_PATH",
        help="Use this generated dataset instead of the latest configured dataset.",
    )
    parser.add_argument(
        "--scenario-id", help="Choose a specific scenario instead of a random sample.",
    )
    parser.add_argument(
        "--no-random", action="store_true",
        help="Use the first dataset sample unless --scenario-id is supplied.",
    )
    parser.add_argument("--pause", action="store_true", help="Wait for Enter between stages.")
    args = parser.parse_args(argv)
    if args.replay and args.scenario_id is not None:
        parser.error("--scenario-id selects a dataset sample and cannot be used with --replay")

    print("Concerted Abduction: LM + DST demonstration", flush=True)
    print("Belief masses are research estimates, not calibrated diagnostic probabilities.")
    extractor = creator = assigner = fod = None

    if args.replay:
        print(f"REPLAY: saved LM outputs from {args.replay}; no API calls.")
        fod = FodOutput.model_validate_json((args.replay / "frame.json").read_text())
        sample_path = args.replay / "input.json"
        sample = DataSample.model_validate_json(sample_path.read_text()) if sample_path.exists() else None
        responses = fod.hypotheses
        output_dir = None
        combiner = DempsterCombination()
        combination_name = "Dempster"
    else:
        env = ENVSettings()
        settings = ConcertedAbductionSettings()  # pyright: ignore[reportCallIssue]
        configs = (settings.fod_extractor, settings.focal_set, settings.bpa)
        if any(c.llm and c.llm.provider == "google_genai" for c in configs) and not env.gemini_api_key:
            raise ValueError("Set GEMINI_API_KEY in .env, or use --replay SCENARIO_DIR.")
        dataset_path = (
            args.dataset.resolve() if args.dataset
            else latest_run_dir(settings.data_generator.output_dir) / "generated_dataset.json"
        )
        sample = load_sample(dataset_path, args.scenario_id, random_sample=not args.no_random)
        responses = {entry.source: entry.response for entry in sample.outputs}
        extractor = configured(FodExtractorRegistry._get(settings.fod_extractor.type), settings.fod_extractor)
        creator = configured(FocalSetRegistry._get(settings.focal_set.type), settings.focal_set)
        assigner = configured(BpaRegistry._get(settings.bpa.type), settings.bpa)
        combiner = CombinerRegistry._get(settings.combiner.type)()
        combination_name = settings.combiner.type
        base_dir = settings.bpa.output_dir / "demos"
        base_dir.mkdir(parents=True, exist_ok=True)
        output_dir = Path(mkdtemp(prefix="demo-", dir=base_dir))
        save(output_dir, "input.json", sample)
        save_run_metadata(
            output_dir, mode="live_demo", dataset_path=str(dataset_path),
            scenario_id=sample.scenario_id, settings=settings.model_dump(mode="json"),
        )
        print("LIVE: generated synthetic sample; frame, focal sets, and masses use real LM calls.")
        print(f"Dataset: {dataset_path}")
        print(f"Artifacts are saved after each stage to: {output_dir}", flush=True)

    stage("1. Source responses", "A common question and its source responses", False)
    if sample:
        print(f"Scenario: {sample.scenario_id}")
    if sample:
        console.print(Text(f"Question: {sample.input_message}", style="bold #ff8c00"))
    else:
        console.print("Original question was not saved in this scenario folder.")
    table(["Source", "Response"], responses.items())

    stage("2. Frame of discernment", "All source responses", args.pause)
    if not args.replay:
        assert extractor is not None and sample is not None and output_dir is not None
        with console.status("Waiting for LM: extracting the frame of discernment..."):
            fod = extractor.generate_frame(sample)
        save(output_dir, "frame.json", fod)
    assert fod is not None
    table(["Hypothesis"], [[label] for label in fod.frame.frame])

    stage("3. Focal-set extraction", "Shared frame + all source responses", args.pause)
    if args.replay:
        focal_sets = FocalSetOutput.model_validate_json((args.replay / "focal_sets.json").read_text())
    else:
        assert creator is not None and output_dir is not None
        with console.status("Waiting for LM: extracting focal sets..."):
            focal_sets = creator.create_focal_sets(fod)
        save(output_dir, "focal_sets.json", focal_sets)
    table(
        ["Source", "Focal set", "Justification", "Source excerpts"],
        [
            [source_sets.source, subset(focal.hypotheses), focal.justification,
             "\n".join(f'"{citation}"' for citation in focal.citations)]
            for source_sets in focal_sets.sources for focal in source_sets.focal_sets
        ],
    )
    for warning in focal_sets.validation_errors:
        print(f"Validation warning: {warning}")

    stage("4. Belief-mass assignment", "Each source's text + its focal sets + shared frame", args.pause)
    if args.replay:
        bpa = BpaOutput.model_validate_json((args.replay / "bpa.json").read_text())
    else:
        assert assigner is not None and output_dir is not None
        with console.status(
            f"Waiting for LM: assigning belief masses ({len(fod.hypotheses)} sources)..."
        ):
            bpa = assigner.assign_masses(fod, focal_sets)
        save(output_dir, "bpa.json", bpa)
    table(
        ["Source", "Focal set", "Mass", "Justification"],
        [
            [source_bpa.source, subset(mass.hypotheses), f"{mass.mass:.2%}", mass.justification]
            for source_bpa in bpa.sources for mass in source_bpa.masses
        ],
    )
    print("Mass on the full frame preserves uncertainty; it is not split between its members.")

    stage(f"5. Evidence combination ({combination_name})", "All source mass functions; no source text", args.pause)
    combined, conflict = combiner.combine(bpa)
    table(
        ["Focal set", "Combined mass"],
        [[subset(entry.focal_set), f"{entry.combined_mass:.2%}"] for entry in combined.combined_masses],
    )
    conflict_text = f"Conflict: {conflict:.2%}"
    console.print(Text(conflict_text, style="bold red"))
    if output_dir:
        (output_dir / "combined.json").write_text(
            json.dumps(combined.model_dump(mode="json") | {"conflict": conflict}, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
