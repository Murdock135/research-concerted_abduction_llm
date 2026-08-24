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

## Run the prototype pipeline

```bash
python scripts/pipeline_prototype.py
```

- Loads `generated_dataset.json` from the latest run under `data_generator.output_dir`.
- For each sample, resolves the configured `fod_extractor` implementation via `FodExtractorRegistry._get(cfg.type)` (default: `LanguageModelFodExtractor`, registered as `"language_model_fod_extractor"`) and runs it over that sample's model outputs to produce a frame of discernment.
- Writes `<fod_extractor.output_dir>/<run>/<scenario_id>_frame.json` for each sample.
- Stops there today — mass function assignment and evidence combination are not implemented, so this does not yet produce a final combined belief distribution. See [roadmap.md](roadmap.md).

## Tests

None yet — `tests/` only contains a `.gitkeep`.

---
Next: [extending.md](extending.md) — how to plug in a new generator/extractor implementation.
