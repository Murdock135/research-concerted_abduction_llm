# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research project implementing **Concerted Abduction** with LLMs: combining outputs from multiple LLMs using Dempster-Shafer Theory (belief functions) to synthesize conclusions from conflicting/overlapping model responses. Domain focus is medical diagnosis.

## Development Setup

```bash
uv sync          # Install dependencies
```

API credentials go in a `.env` file at the project root as `GEMINI_API_KEY=...` (loaded via dotenv).

## Running Scripts

```bash
python scripts/generate_data.py       # Generate synthetic dataset via Gemini API → data/generated_dataset.json
python scripts/pipeline_prototype.py  # Run the prototype abduction pipeline
```

No tests currently exist (`tests/` is empty).

## Architecture

The pipeline flows:

1. **Data generation** (`src/concerted_abduction/data_utils/data_generator.py`) — `CommonInputDataGenerator` calls Gemini with structured JSON schema to produce synthetic scenarios where 3 named models (Model A/B/C) give different responses to the same input.

2. **Dataset types** (`src/concerted_abduction/types.py`) — Pydantic models: `DataSample` (one scenario), `ModelOutput` (one model's response), `DataSet` (collection), `OverlapMatrix` (n×n similarity matrix).

3. **Hypothesis extraction** (`src/concerted_abduction/extractors/`) — `HypothesisExtractor` abstract base; `LlmHypothesisExtractor` uses Gemini to read all model outputs and produce a Universe of Discourse (UoD). `ExtractorRegistry` lets components be registered and retrieved by name.

4. **Planned but empty:** `src/concerted_abduction/mass_functions/`, `src/concerted_abduction/combiners/`, `src/concerted_abduction/integrations/`, `config/settings.py`.

## Key Conventions

- Prompts live in `prompts/` and are loaded via `load_prompt()` from `src/concerted_abduction/utils/utils.py`.
- Example data for prompting lives in `data/synthetic/examples/`.
- Generated datasets go to `data/generated_dataset.json` or `data/synthetic/generated/`.
- `find_project_root()` traverses up from `__file__` to locate `pyproject.toml`.
- Python ≥ 3.13 required; uses `uv_build` as build backend.
- All LLM calls use the `google-genai` SDK with structured output (JSON schema from Pydantic models).

## Current TODO

- Implement mass function assignment (`ca/mass_functions/`)
- Implement evidence combiners (`ca/combiners/`)
- Add environment variable loading helper
- Add `config.toml` for configuring component prompts, example files, LLM selection per component, and output directories
