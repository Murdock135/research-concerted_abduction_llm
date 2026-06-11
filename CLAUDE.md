# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Research project implementing **Concerted Abduction with LLMs** — a pipeline that uses multiple LLMs to generate hypotheses and combines their outputs using Dempster-Shafer theory of evidence. The goal is to aggregate partial, uncertain beliefs from different LLM sources into a unified universe of discourse.

## Commands

This project uses `uv` for dependency management (Python 3.13).

```bash
# Install dependencies
uv sync

# Run the data generation script
uv run python scripts/generate_data.py

# Run the pipeline prototype
uv run python scripts/pipeline_prototype.py
```

**API keys** are loaded from `~/.secrets/.llm_apis` via `python-dotenv`. The required key is `GEMINI_API_KEY`.

## Architecture

### Package: `src/concerted_abduction/`

The pipeline has three planned stages (hypothesis extraction is partially implemented; mass functions and combiners are stubs):

1. **Hypothesis Extraction** (`extractors/`) — given multiple LLM outputs for the same prompt, extract a shared universe of discourse (UoD)
2. **Mass Function Assignment** (`mass_functions/`) — assign confidence/belief values per hypothesis (stub)
3. **Evidence Combination** (`combiners/`) — combine mass functions using Dempster's rule (stub)

**Key modules:**

- `types.py` — Pydantic models: `ModelOutput`, `DataSample`, `DataSet`, `OverlapMatrix`. `DataSet` is the primary data container throughout the pipeline.
- `extractors/base.py` — Abstract `HypothesisExtractor` with a single method `create_uod(inputs)`.
- `extractors/registry.py` — `ExtractorRegistry` using a `@register(name)` class decorator to register extractor implementations.
- `extractors/llm.py` — `LlmHypothesisExtractor`: calls Google GenAI (`gemini-2.5-flash`) with a configurable class-level `system_prompt`.
- `data_utils/data_generator.py` — `CommonInputDataGenerator`: uses GenAI structured output (JSON schema from `DataSet.model_json_schema()`) to synthetically generate datasets. Loads its system prompt from `prompts/data_generators/common_input/v0.txt` and few-shot examples from `data/synthetic/examples/common_input/v0.json`.
- `utils/utils.py` — `find_project_root()` (walks up to `.git`) and `load_prompt()` (reads `.txt` prompt files).

### Data Layout

```
data/
  generated_dataset.json          # output of generate_data.py
  synthetic/
    examples/common_input/v0.json # few-shot examples fed to data generator
    generated/common_input/v0.json
prompts/
  data_generators/common_input/v0.txt  # system prompt for data generator
experiments/
  runs/prototype/                 # experiment outputs
```

Prompts and example files are versioned (`v0`, `v1`, …) and referenced by path. `find_project_root()` is used to resolve absolute paths so scripts can be run from any working directory.

### LLM Integration

The primary LLM SDK is `google-genai` (`from google import genai`). Structured outputs use `response_mime_type="application/json"` with `response_json_schema` from Pydantic models. The `integrations/` directory contains alternative wrappers (LangChain, OpenAI, Gemini) that are not yet used in the main pipeline.

### Planned Work (from `todo.md`)

- Helper to load env variables centrally
- `config.toml` to configure prompts, examples, LLMs, and output dirs per pipeline component
