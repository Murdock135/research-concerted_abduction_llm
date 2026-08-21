"""Run the configuration-driven Concerted Abduction pipeline.

The project combines outputs from multiple language models using a staged
abductive-reasoning pipeline:

1. Generate or load model responses to a common input.
2. Extract a frame of discernment (the candidate hypotheses).
3. Assign belief masses to those hypotheses.
4. Combine evidence using Dempster-Shafer theory.

Current state:
    This runner loads the most recently generated dataset and executes the
    configured hypothesis-extraction implementation. Mass assignment and
    evidence combination will be added here once those stages are implemented.

TODO:
    - [x] Refactor hypothesis extraction into concerted_abduction.extractors.
    - [x] Add configuration-driven component and LLM-provider construction.
    - [ ] Implement and integrate mass-function assignment.
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

from concerted_abduction.extractors import ExtractorRegistry, HypothesisExtractor
from concerted_abduction.types import DataSet, ExtractorOutput
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
        description="Run hypothesis extraction using the configured implementation."
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


def create_extractor(cfg: ComponentConfig) -> HypothesisExtractor:
    """Resolve an extractor and construct it through its config adapter."""
    extractor_cls = ExtractorRegistry.get(cfg.type)
    from_config: Any = getattr(extractor_cls, "from_config", None)
    if not callable(from_config):
        raise TypeError(
            f"Configured extractor {cfg.type!r} does not provide from_config()"
        )

    extractor = from_config(cfg)
    if not isinstance(extractor, HypothesisExtractor):
        raise TypeError(
            f"{extractor_cls.__name__}.from_config() did not return an extractor"
        )
    return extractor


def save_frame(run_dir: Path, sample_id: str, result: ExtractorOutput) -> None:
    output_path = run_dir / f"{sample_id}_frame.json"
    output_path.write_text(
        json.dumps(result.model_dump(), ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    env = ENVSettings()
    # Pydantic Settings supplies these required fields from TOML at runtime.
    settings = ConcertedAbductionSettings()  # pyright: ignore[reportCallIssue]
    extractor_cfg = settings.hypothesis_extractor

    if (
        extractor_cfg.llm is not None
        and extractor_cfg.llm.provider == "google_genai"
        and not env.gemini_api_key
    ):
        raise EnvironmentError("GEMINI_API_KEY was not found in the environment")

    data_path = (
        latest_run_dir(settings.data_generator.output_dir)
        / "generated_dataset.json"
    )
    dataset = load_dataset(data_path)
    if not dataset.samples:
        raise ValueError(f"Dataset contains no samples: {data_path}")

    extractor = create_extractor(extractor_cfg)
    samples = dataset.samples if args.all else dataset.samples[: args.num_samples]

    run_dir = make_run_dir(extractor_cfg.output_dir)
    save_run_metadata(
        run_dir,
        dataset_path=str(data_path),
        extractor_type=extractor_cfg.type,
        prompt_path=str(extractor_cfg.prompt_path),
        provider=(extractor_cfg.llm.provider if extractor_cfg.llm else None),
        model=(extractor_cfg.llm.model_name if extractor_cfg.llm else None),
        sample_count=len(samples),
        smoke_test=not args.all,
    )

    for sample in samples:
        result = extractor.generate_frame(sample)
        save_frame(run_dir, sample.scenario_id, result)
        print(f"Processed {sample.scenario_id} -> {run_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
