# Configuration

Configuration is layered, resolved by `src/config/settings.py`:

1. **Bundled defaults** — `src/config/default_config.toml` (always loaded)
2. **Project overrides** — `config.toml` at the project root (optional, deep-merged over defaults)
3. **Environment / secrets** — `.env` at the project root (API keys, loaded via dotenv-style `ENVSettings`)

## `ENVSettings`

Loads API credentials into `os.environ` at construction time (`model_post_init`). Reads from `<project_root>/.env` (`ENV_PATH` in `settings.py`, gitignored). Currently only knows about:

```
GEMINI_API_KEY=...
```

Every script that calls the Gemini API constructs `ENVSettings()` first and raises `EnvironmentError` if `gemini_api_key` is missing, e.g. `scripts/generate_data.py` and `scripts/pipeline_prototype.py`.

## `ConcertedAbductionSettings`

The main settings object has five sections: `data_generator`, `fod_extractor`,
`focal_set`, `bpa`, and `combiner`. The LLM-backed stages use `ComponentConfig`;
combination uses `CombinerConfig`, which extends it with `numerical_tolerance`.

```toml
[data_generator]
type = "common_input"
prompt_path = "prompts/data_generators/common_input/v0.txt"
examples_path = "data/synthetic/examples/common_input/v0.json"
output_dir = "data"

[data_generator.llm]
provider = "google_genai"
model = "gemini-2.5-flash"

[fod_extractor]
type = "language_model_fod_extractor"
prompt_path = "prompts/fod/v0.txt"
output_dir = "experiments/runs"

[fod_extractor.llm]
provider = "google_genai"
model = "gemini-2.5-flash"

[focal_set]
type = "language_model_focal_set_creator"
prompt_path = "prompts/focal_set/v0.txt"
output_dir = "experiments/runs"

[focal_set.llm]
provider = "google_genai"
model = "gemini-2.5-flash"
```

The bundled defaults additionally contain:

```toml
[bpa]
type = "language_model_bpa_assigner"
prompt_path = "prompts/bpa/v0.txt"
output_dir = "experiments/runs"

[bpa.llm]
provider = "google_genai"
model = "gemini-2.5-flash"

[combiner]
type = "dempster"
output_dir = "experiments/runs"
numerical_tolerance = 1e-12
```

Combination uses no LLM. For Dempster's rule, `numerical_tolerance` must be finite
and strictly between zero and one. A step with surviving non-conflicting mass at
or below it raises `TotalConflictError`. This is distinct from the source BPA
sum-to-one tolerance (`1e-6`). All four analysis-stage output directories must
match so artifacts are saved in one run directory. The root `config.toml` selects
Dempster and otherwise inherits bundled defaults.

### `ComponentConfig` fields

| field | type | meaning |
|---|---|---|
| `type` | `str` | Registry name of the implementation to use (looked up via `DataGeneratorRegistry._get(type)` / `FodExtractorRegistry._get(type)`) |
| `output_dir` | `Path` | Where this component writes its output |
| `llm` | `LLMSetting \| None` | `{provider, model, temperature?}` — which LLM this component calls |
| `prompt_path` | `Path \| None` | Prompt file loaded via `load_prompt()` |
| `examples_path` | `Path \| None` | Few-shot examples file (only used by the data generator today) |

Relative paths in `config.toml` (including `output_dir`) are resolved against the project root (the directory containing `pyproject.toml`/`.git`), not the current working directory — see `ComponentConfig.resolve_path`.

## Overriding defaults

To use a different model, prompt, or implementation for a component, create a `config.toml` at the project root with only the keys you want to override — it's deep-merged on top of `default_config.toml`:

```toml
[fod_extractor.llm]
model = "gemini-2.5-pro"
```

This is enough to switch just the FoD extractor's model while leaving everything else (data generator config, prompt paths, etc.) at their defaults.

## Accessing settings in code

```python
from config.settings import ENVSettings, ConcertedAbductionSettings

env = ENVSettings()  # populates os.environ["GEMINI_API_KEY"]
settings = ConcertedAbductionSettings()
gen_cfg = settings.data_generator
extractor_cfg = settings.fod_extractor
focal_set_cfg = settings.focal_set
```

---
Next: [usage.md](usage.md) — the actual commands to run, now that setup/config is covered.
