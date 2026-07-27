# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research project implementing **Concerted Abduction** with LLMs: combining outputs from multiple LLMs using Dempster-Shafer Theory (belief functions) to synthesize conclusions from conflicting/overlapping model responses. Domain focus is medical diagnosis.

Full documentation lives in `docs/` — start at [docs/README.md](docs/README.md) (or [docs/overview.md](docs/overview.md) for the research idea, [docs/architecture.md](docs/architecture.md) for how the code fits together, [docs/configuration.md](docs/configuration.md) for `config.toml`/`settings.py`, [docs/roadmap.md](docs/roadmap.md) for what's implemented vs. planned).

## Development Setup

```bash
uv sync          # Install dependencies
```

Requires Python ≥ 3.13. API credentials go in a `.env` file at the project root as `GEMINI_API_KEY=...`, loaded via `ENVSettings` (`src/config/settings.py`).

## Running Scripts

```bash
uv run python scripts/generate_data.py       # Generate synthetic dataset via Gemini API → data/generated_dataset.json
uv run python scripts/pipeline_prototype.py  # Run the prototype abduction pipeline
```

No tests currently exist (`tests/` is empty).

## Architecture

The pipeline has four stages, each an abstract component with pluggable implementations looked up by name through a registry, configured via `config.toml`/`src/config/default_config.toml` (see [docs/configuration.md](docs/configuration.md)):

1. **Data generation** (`src/concerted_abduction/data_utils/`) — `CommonInputDataGenerator` calls Gemini with a structured JSON schema to produce synthetic scenarios where 3 named models (Model A/B/C) give different responses to the same input. Registry: `DataGeneratorRegistry`.
2. **Hypothesis extraction** (`src/concerted_abduction/extractors/`) — `HypothesisExtractor` abstract base; `LlmHypothesisExtractor` uses Gemini to read all model outputs and produce a Universe of Discourse (UoD). Registry: `ExtractorRegistry`.
3. **Mass function assignment** (`src/concerted_abduction/mass_functions/`) — not implemented yet.
4. **Evidence combination** (`src/concerted_abduction/combiners/`) — not implemented yet (Dempster's rule).

**Dataset types** (`src/concerted_abduction/types.py`) — Pydantic models: `DataSample` (one scenario), `ModelOutput` (one model's response), `DataSet` (collection), `OverlapMatrix` (n×n similarity matrix).

See [docs/architecture.md](docs/architecture.md) for full detail and [docs/data_model.md](docs/data_model.md) for the schema.

## Key Conventions

- Prompts live in `prompts/` and are loaded via `load_prompt()` from `src/concerted_abduction/utils/utils.py`.
- Example data for prompting lives in `data/synthetic/examples/`.
- Generated datasets go to `data/generated_dataset.json` or `data/synthetic/generated/`.
- `find_project_root()` traverses up from `__file__` to locate `.git`.
- Python ≥ 3.13 required; uses `uv_build` as build backend.
- All LLM calls use the `google-genai` SDK with structured output (JSON schema from Pydantic models) where supported.
- Component behavior (LLM/prompt/examples/output dir) is configured via `config.toml` (deep-merged over `src/config/default_config.toml`), not hardcoded — see [docs/configuration.md](docs/configuration.md).
- New generators/extractors/mass functions/combiners are added via the base-class + registry pattern — see [docs/extending.md](docs/extending.md).

## Current TODO

See [docs/roadmap.md](docs/roadmap.md) for the up-to-date list. Headline items:

- Implement mass function assignment (`src/concerted_abduction/mass_functions/`)
- Implement evidence combiners (`src/concerted_abduction/combiners/`)
