# Concerted Abduction

Research project combining outputs from multiple LLMs using Dempster-Shafer Theory (belief functions) to synthesize conclusions from conflicting or overlapping model responses. Domain focus is medical diagnosis.

## What this is

Instead of relying on a single model or naively voting/averaging across multiple models, this project explores treating each LLM's response as partial evidence and combining that evidence using Dempster-Shafer evidence theory. The goal is a pipeline that takes several models' answers to the same input and produces a reconciled belief distribution over possible diagnoses, accounting for agreement, disagreement, and overlap between sources.

## Status

Early-stage research code. Working today:

- Synthetic dataset generation (multiple model outputs per scenario)
- Typed dataset schema
- LLM-based frame-of-discernment (FoD) extraction
- LLM-based focal-set creation with source-text citations

- LLM-based source BPA assignment with distribution validation
- Registry-selected Dempster evidence combination
- Complete runner with per-scenario error logs and batch summaries

## Setup

```bash
uv sync
```

API credentials go in a `.env` file at the project root:

```
GEMINI_API_KEY=...
```

## Usage

```bash
uv run python scripts/generate_data.py  # Generate a timestamped synthetic dataset
uv run python scripts/run.py            # Process one scenario through combination
```

Run the unit tests with:

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

## Architecture

1. **Data generation** (`src/concerted_abduction/data_utils/data_generator.py`) — `CommonInputDataGenerator` calls Gemini with a structured JSON schema to produce synthetic scenarios where 3 named models (Model A/B/C) give different responses to the same input.
2. **Dataset types** (`src/concerted_abduction/types.py`) — Pydantic models: `DataSample` (one scenario), `ModelOutput` (one model's response), `DataSet` (collection), `OverlapMatrix` (n×n similarity matrix).
3. **Frame-of-discernment extraction** (`src/concerted_abduction/fod/`) — `FrameOfDiscernmentExtractor` abstract base; `LanguageModelFodExtractor` uses Gemini to read all model outputs and produce a frame of discernment (FoD). `FodExtractorRegistry` lets components be registered and retrieved by name.
4. **Focal-set creation** (`src/concerted_abduction/focal_set/`) — `LanguageModelFocalSetCreator` derives subsets of the FoD for each source, explains each subset, and cites verbatim supporting excerpts.
5. **Mass assignment** (`src/concerted_abduction/bpa/`) — assigns and validates source masses.
6. **Evidence combination** (`src/concerted_abduction/combiners/`) — combines source BPAs and returns normalized masses plus conflict.

## Project layout

```
src/concerted_abduction/  Core library (types, fod, focal_set, data_utils, bpa, combiners)
prompts/                  Prompt templates, loaded via load_prompt()
data/                     Example data and generated datasets
scripts/                  Runnable entry points (generate_data.py, run.py)
integrations/             LLM provider integrations (gemini, langchain, openai)
config/                   Project configuration (settings.py)
docs/                     Reference notes
experiments/              Experiment run outputs
notebooks/                Scratch notebooks
```

## Key conventions

- Prompts live in `prompts/` and are loaded via `load_prompt()` from `src/concerted_abduction/utils/utils.py`.
- Example data for prompting lives in `data/synthetic/examples/`.
- Generated datasets go to `data/generated_dataset.json` or `data/synthetic/generated/`.
- `find_project_root()` traverses up from `__file__` to locate `pyproject.toml`.
- Python ≥ 3.13 required; uses `uv_build` as the build backend.
- All LLM calls use the `google-genai` SDK with structured output (JSON schema from Pydantic models).

## Roadmap

The prototype pipeline is implemented through combined masses. Research evaluation,
BPA calibration, and treatment of source dependence remain open. See
[docs/roadmap.md](docs/roadmap.md).
