# Configuration

Configuration is layered, resolved by `src/config/settings.py`:

1. **Bundled defaults** — `src/config/default_config.toml` (always loaded)
2. **Project overrides** — `config.toml` at the project root (optional; not present by default — copy/create one to override defaults, it's deep-merged on top)
3. **Environment / secrets** — `~/.secrets/.llm_apis` (API keys, loaded via dotenv-style `ENVSettings`)

## `ENVSettings`

Loads API credentials into `os.environ` at construction time (`model_post_init`). Reads from `~/.secrets/.llm_apis` (path resolved as `<project_root>/.env`... actually resolved via `find_project_root(__file__).resolve() / ".env"` — see note below). Currently only knows about:

```
GEMINI_API_KEY=...
```

Every script that calls the Gemini API constructs `ENVSettings()` first and raises `EnvironmentError` if `gemini_api_key` is missing, e.g. `scripts/generate_data.py` and `scripts/pipeline_prototype.py`.

> Note: despite the docstring/CLAUDE.md saying `~/.secrets/.llm_apis`, `ENV_PATH` in `settings.py` is computed as `find_project_root(__file__).resolve() / ".env"` — i.e. it actually looks for a `.env` file at the project root, not `~/.secrets/.llm_apis`. If you hit `EnvironmentError: GEMINI_API_KEY not found`, check which of the two paths your key is actually in.

## `ConcertedAbductionSettings`

The main settings object. Two top-level sections currently, one per pipeline component:

```toml
[data_generator]
type = "common_input"
prompt_path = "prompts/data_generators/common_input/v0.txt"
examples_path = "data/synthetic/examples/common_input/v0.json"
output_dir = "data"

[data_generator.llm]
provider = "google_genai"
model = "gemini-2.5-flash"

[hypothesis_extractor]
type = "llm_hypothesis_extractor"
prompt_path = "prompts/extractors/hypothesis/v0.txt"
output_dir = "experiments/runs"

[hypothesis_extractor.llm]
provider = "google_genai"
model = "gemini-2.5-flash"
```

This is the content of `src/config/default_config.toml`. `hypothesis_extractor` has no `examples_path` set by default.

### `ComponentConfig` fields

| field | type | meaning |
|---|---|---|
| `type` | `str` | Registry name of the implementation to use (looked up via `DataGeneratorRegistry.get(type)` / `ExtractorRegistry.get(type)`) |
| `output_dir` | `Path` | Where this component writes its output |
| `llm` | `LLMSetting \| None` | `{provider, model, temperature?}` — which LLM this component calls |
| `prompt_path` | `Path \| None` | Prompt file loaded via `load_prompt()` |
| `examples_path` | `Path \| None` | Few-shot examples file (only used by the data generator today) |

Relative paths in `config.toml` (including `output_dir`) are resolved against the project root (the directory containing `pyproject.toml`/`.git`), not the current working directory — see `ComponentConfig.resolve_path`.

## Overriding defaults

To use a different model, prompt, or implementation for a component, create a `config.toml` at the project root with only the keys you want to override — it's deep-merged on top of `default_config.toml`:

```toml
[hypothesis_extractor.llm]
model = "gemini-2.5-pro"
```

This is enough to switch just the hypothesis extractor's model while leaving everything else (data generator config, prompt paths, etc.) at their defaults.

## Accessing settings in code

```python
from config.settings import ENVSettings, ConcertedAbductionSettings

env = ENVSettings()  # populates os.environ["GEMINI_API_KEY"]
settings = ConcertedAbductionSettings()
gen_cfg = settings.data_generator
extractor_cfg = settings.hypothesis_extractor
```

---
Next: [usage.md](usage.md) — the actual commands to run, now that setup/config is covered.
