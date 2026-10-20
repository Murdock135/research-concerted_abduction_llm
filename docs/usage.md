# Usage

## Setup

```bash
uv sync
```

Requires Python ≥ 3.13. Put your Gemini API key in a `.env` file at the project root as `GEMINI_API_KEY=...` — see [configuration.md](configuration.md) for how `ENVSettings` loads it.

## Generate synthetic data

```bash
python scripts/generate_data.py
```

- Reads `data_generator` config from `config.toml`/`default_config.toml` and resolves the generator implementation via `DataGeneratorRegistry.get(cfg.type)` — whichever generator is registered under that name is what runs (default: `CommonInputDataGenerator`, registered as `"common_input"`; see [architecture.md](architecture.md)).
- Instantiates it with the configured LLM and examples file.
- Sends a hardcoded example prompt requesting 5 medical-diagnosis scenarios across 3 models with a given overlap matrix (see `scripts/generate_data.py` if you want to change the prompt/count/domain — it's not yet parameterized via CLI args).
- Writes the resulting `DataSet` to `<data_generator.output_dir>/<run>/generated_dataset.json`.

## Run the pipeline

```bash
uv run python scripts/run.py
uv run python scripts/run.py --num-samples 5
uv run python scripts/run.py --all
```

- Loads `generated_dataset.json` from the latest run under `data_generator.output_dir`.
- For each sample, resolves the configured `fod_extractor` implementation via `FodExtractorRegistry._get(cfg.type)` (default: `LanguageModelFodExtractor`, registered as `"language_model_fod_extractor"`) and runs it over that sample's model outputs to produce a frame of discernment.
- Passes each `FodOutput` to the configured `focal_set` implementation (default: `LanguageModelFocalSetCreator`, registered as `"language_model_focal_set_creator"`).
- Assigns source masses with the configured BPA assigner and writes `<scenario_id>/frame.json`, `<scenario_id>/focal_sets.json`, and `<scenario_id>/bpa.json`. The extractor, focal-set creator, BPA assigner, and combiner must share an output directory.
- Processes one sample by default to limit API usage. Use `--num-samples N` or `--all` to process more.
- A failed scenario writes `<scenario_id>/error.json` with its stage, error type, and message. Earlier stage outputs are preserved, and later scenarios continue.
- At the end, `summary.json` lists scenario outcomes and success/failure counts. The command exits with status 1 if any scenario failed, otherwise 0. Setup errors stop the run; Ctrl+C still interrupts it.
- Each scenario has its own folder under the run directory. Scenario IDs are URL-encoded (including dots) for safe folder names and must be non-empty and unique within the selected samples. `metadata.json` and `summary.json` remain at the run root.
- Combines the source BPAs using the configured combiner (default: `Dempster`). Writes `<scenario_id>/combined.json` containing `combined_masses` and `conflict`. The combiner makes no LLM calls.

## Demonstrate the process

```bash
uv run python scripts/demo.py --pause
```

The demo picks a random sample from the latest generated synthetic dataset on each run, then
uses the configured LM components to extract the frame, extract cited focal sets, and assign belief
masses. The configured combiner produces combined masses and conflict. Each stage
prints its inputs and presents outputs in Rich tables, wrapping long text to fit
the terminal, aligning masses, and highlighting conflict in red;
`--pause` waits for Enter between stages. Omit it
to run continuously. Live results may differ from the illustrative diagram.
Artifacts are saved after each stage in a unique folder under
`<bpa.output_dir>/demos/`. The source dataset path and scenario ID are printed and
recorded in the run metadata. Use `--no-random` to select the first sample,
`--scenario-id` to select a specific sample (overriding random selection), or
`--dataset` to select a specific generated dataset. Random selection can repeat
a sample across runs; replay always uses the saved scenario.

```bash
uv run python scripts/demo.py --no-random --pause
uv run python scripts/demo.py --scenario-id sample_high_02 --pause
uv run python scripts/demo.py --dataset data/synthetic/generated/common_input/14_10_2026-20_34_49/generated_dataset.json --scenario-id sample_high_01
```

For a presentation without API calls, replay a completed scenario folder:

```bash
uv run python scripts/demo.py --replay experiments/runs/13_10_2026-18_35_12/1 --pause
```

Replay reads `frame.json`, `focal_sets.json`, and `bpa.json`, displays those saved
LM outputs, and recomputes the result using Dempster's rule. It does not modify
the saved files. Demo folders also include `input.json` so the original question
can be displayed on replay; older scenario folders may lack it.

## Tests

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

---
Next: [extending.md](extending.md) — how to plug in a new generator/extractor implementation.
