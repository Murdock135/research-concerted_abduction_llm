"""Run the configuration-driven Concerted Abduction pipeline.

The project combines outputs from multiple language models using a staged
abductive-reasoning pipeline:

1. Generate or load model responses to a common input.
2. Extract a frame of discernment (the candidate hypotheses).
3. Create cited focal sets for each source.
4. Assign belief masses to those focal sets.
5. Combine evidence using Dempster-Shafer theory.

Current state:
    This runner loads the most recently generated dataset and executes the
    configured frame-of-discernment extractor, focal-set creator, and BPA
    assigner. Evidence combination remains to be implemented.

TODO:
    - [x] Refactor frame extraction into concerted_abduction.fod.
    - [x] Integrate focal-set creation.
    - [x] Add configuration-driven component and LLM-provider construction.
    - [x] Implement and integrate mass-function assignment.
    - [ ] Implement and integrate evidence combination using Dempster's rule.
    - [ ] Add automated tests for the complete pipeline.

The component implementation, language-model provider, model, prompt, input
directory, and output directory are selected through the project's layered
TOML configuration.

By default, only one sample is processed so the script can serve as a cheap
end-to-end smoke test. Use ``--num-samples`` to select a prefix of the dataset
or ``--all`` to process the complete dataset.

Examples:
    uv run python scripts/run.py
    uv run python scripts/run.py --num-samples 5
    uv run python scripts/run.py --all
"""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from concerted_abduction.bpa import BpaAssigner, BpaRegistry
from concerted_abduction.focal_set import FocalSetCreator, FocalSetRegistry
from concerted_abduction.fod import FodExtractorRegistry, FrameOfDiscernmentExtractor
from concerted_abduction.types import BpaOutput, DataSet, FocalSetOutput, FodOutput
from concerted_abduction.utils.run_utils import (
    latest_run_dir,
    make_run_dir,
    save_run_metadata,
)
from config.settings import ComponentConfig, ConcertedAbductionSettings, ENVSettings


def positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run FoD extraction, focal-set creation, and BPA assignment."
    )
    sample_group = parser.add_mutually_exclusive_group()
    sample_group.add_argument(
        "-n",
        "--num-samples",
        type=positive_int,
        default=1,
        metavar="N",
        help="Process the first N samples (default: 1).",
    )
    sample_group.add_argument(
        "--all",
        action="store_true",
        help="Process every sample.",
    )
    return parser.parse_args(argv)


def load_dataset(path: Path) -> DataSet:
    """Load and validate a generated dataset."""
    return DataSet.model_validate_json(path.read_text(encoding="utf-8"))


def create_extractor(cfg: ComponentConfig) -> FrameOfDiscernmentExtractor:
    """Resolve an extractor and construct it through its config adapter."""
    extractor_cls = FodExtractorRegistry._get(cfg.type)

    from_config: Any = getattr(extractor_cls, 'from_config', None)
    if not callable(from_config):
        raise TypeError(f"Configured extractor {extractor_cls.__name__} does not provide `from_config()`.")

    extractor = from_config(cfg)
    if not isinstance(extractor, FrameOfDiscernmentExtractor):
        raise TypeError(
            f"{extractor_cls.__name__}.from_config() returned "
            f"{type(extractor).__name__}, expected a FrameOfDiscernmentExtractor"
        )
    return extractor


def create_focal_set_creator(cfg: ComponentConfig) -> FocalSetCreator:
    """Resolve a focal-set creator and construct it through its config adapter."""
    creator_cls = FocalSetRegistry._get(cfg.type)

    from_config: Any = getattr(creator_cls, "from_config", None)
    if not callable(from_config):
        raise TypeError(
            f"Configured focal-set creator {creator_cls.__name__} does not "
            "provide `from_config()`."
        )

    creator = from_config(cfg)
    if not isinstance(creator, FocalSetCreator):
        raise TypeError(
            f"{creator_cls.__name__}.from_config() returned "
            f"{type(creator).__name__}, expected a FocalSetCreator"
        )
    return creator


def create_bpa_assigner(cfg: ComponentConfig) -> BpaAssigner:
    assigner_cls = BpaRegistry._get(cfg.type)
    from_config: Any = getattr(assigner_cls, "from_config", None)
    if not callable(from_config):
        raise TypeError(f"{assigner_cls.__name__} does not provide from_config()")
    assigner = from_config(cfg)
    if not isinstance(assigner, BpaAssigner):
        raise TypeError("from_config() must return a BpaAssigner")
    return assigner


def save_bpa(run_dir: Path, sample_id: str, result: BpaOutput) -> None:
    (run_dir / f"{sample_id}_bpa.json").write_text(
        result.model_dump_json(indent=4), encoding="utf-8"
    )


def save_frame(run_dir: Path, sample_id: str, result: FodOutput) -> None:
    output_path = run_dir / f"{sample_id}_frame.json"
    output_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def save_focal_sets(
    run_dir: Path, sample_id: str, result: FocalSetOutput
) -> None:
    output_path = run_dir / f"{sample_id}_focal_sets.json"
    output_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    env = ENVSettings()
    # Pydantic Settings supplies these required fields from TOML at runtime.
    settings = ConcertedAbductionSettings()  # pyright: ignore[reportCallIssue]
    extractor_cfg = settings.fod_extractor
    focal_set_cfg = settings.focal_set
    bpa_cfg = settings.bpa

    if len({cfg.output_dir for cfg in (extractor_cfg, focal_set_cfg, bpa_cfg)}) != 1:
        raise ValueError(
            "fod_extractor, focal_set, and bpa output_dir must match so "
            "pipeline artifacts are written to the same run directory"
        )

    uses_google = any(
        cfg.llm is not None and cfg.llm.provider == "google_genai"
        for cfg in (extractor_cfg, focal_set_cfg, bpa_cfg)
    )
    if uses_google and not env.gemini_api_key:
        raise EnvironmentError("GEMINI_API_KEY was not found in the environment")

    data_path = (
        latest_run_dir(settings.data_generator.output_dir)
        / "generated_dataset.json"
    )
    dataset = load_dataset(data_path)
    if not dataset.samples:
        raise ValueError(f"Dataset contains no samples: {data_path}")

    extractor = create_extractor(extractor_cfg)
    focal_set_creator = create_focal_set_creator(focal_set_cfg)
    bpa_assigner = create_bpa_assigner(bpa_cfg)
    samples = dataset.samples if args.all else dataset.samples[: args.num_samples]

    run_dir = make_run_dir(extractor_cfg.output_dir)
    save_run_metadata(
        run_dir,
        dataset_path=str(data_path),
        fod_extractor={
            "type": extractor_cfg.type,
            "prompt_path": str(extractor_cfg.prompt_path),
            "provider": extractor_cfg.llm.provider if extractor_cfg.llm else None,
            "model": extractor_cfg.llm.model_name if extractor_cfg.llm else None,
        },
        focal_set_creator={
            "type": focal_set_cfg.type,
            "prompt_path": str(focal_set_cfg.prompt_path),
            "provider": focal_set_cfg.llm.provider if focal_set_cfg.llm else None,
            "model": focal_set_cfg.llm.model_name if focal_set_cfg.llm else None,
        },
        bpa=bpa_cfg.model_dump(mode="json"),
        sample_count=len(samples),
        smoke_test=not args.all,
    )

    for sample in samples:
        fod_result = extractor.generate_frame(sample)
        focal_set_result = focal_set_creator.create_focal_sets(fod_result)
        save_frame(run_dir, sample.scenario_id, fod_result)
        save_focal_sets(run_dir, sample.scenario_id, focal_set_result)
        if focal_set_result.validation_errors:
            print(
                f"Warning: {sample.scenario_id} focal sets failed "
                f"{len(focal_set_result.validation_errors)} validation check(s); "
                "the result was preserved; continuing to BPA assignment"
            )
        bpa_result = bpa_assigner.assign_masses(fod_result, focal_set_result)
        save_bpa(run_dir, sample.scenario_id, bpa_result)
        print(f"Processed {sample.scenario_id} -> {run_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
