# Concerted Abduction

Research project combining outputs from multiple LLMs using Dempster-Shafer Theory (belief functions) to synthesize conclusions from conflicting or overlapping model responses. Domain focus is medical diagnosis.

## What this is

Instead of relying on a single model or naively voting/averaging across multiple models, this project explores treating each LLM's response as partial evidence and combining that evidence using Dempster-Shafer evidence theory. The goal is a pipeline that takes several models' answers to the same input and produces a reconciled belief distribution over possible diagnoses, accounting for agreement, disagreement, and overlap between sources.

## Status

Early-stage research code. Working today:

- Synthetic dataset generation (multiple model outputs per scenario)
- Typed dataset schema
- LLM-based frame-of-discernment (FoD) extraction

Not yet implemented:

- Mass function assignment (`src/concerted_abduction/mass_functions/`)
- Evidence combination via Dempster's rule (`src/concerted_abduction/combiners/`)
- The end-to-end pipeline script (`scripts/pipeline_prototype.py`) currently only loads a generated dataset

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
python scripts/generate_data.py       # Generate synthetic dataset via Gemini API -> data/generated_dataset.json
python scripts/pipeline_prototype.py  # Run the (in-progress) prototype abduction pipeline
```

No tests currently exist (`tests/` is empty).

## Architecture

1. **Data generation** (`src/concerted_abduction/data_utils/data_generator.py`) — `CommonInputDataGenerator` calls Gemini with a structured JSON schema to produce synthetic scenarios where 3 named models (Model A/B/C) give different responses to the same input.
2. **Dataset types** (`src/concerted_abduction/types.py`) — Pydantic models: `DataSample` (one scenario), `ModelOutput` (one model's response), `DataSet` (collection), `OverlapMatrix` (n×n similarity matrix).
3. **Frame-of-discernment extraction** (`src/concerted_abduction/fod/`) — `FrameOfDiscernmentExtractor` abstract base; `LanguageModelFodExtractor` uses Gemini to read all model outputs and produce a frame of discernment (FoD). `FodExtractorRegistry` lets components be registered and retrieved by name.
4. **Planned:** mass function assignment, evidence combiners, and a `config.toml`-driven configuration layer.

## Project layout

```
src/concerted_abduction/  Core library (types, fod, data_utils, mass_functions, combiners)
prompts/                  Prompt templates, loaded via load_prompt()
data/                     Example data and generated datasets
scripts/                  Runnable entry points (generate_data.py, pipeline_prototype.py)
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

- Implement mass function assignment (`mass_functions/`)
- Implement evidence combiners (`combiners/`)
- Add an environment variable loading helper
- Add `config.toml` for configuring component prompts, example files, LLM selection per component, and output directories
