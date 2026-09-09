# Contributing

Thanks for contributing. Concerted Abduction is early-stage research software
that explores combining multiple language-model responses with
Dempster-Shafer evidence theory. The first two pipeline stages work; mass
assignment, evidence combination, and comprehensive tests are still planned.

For the research
background, start with [the project overview](docs/overview.md). For current
priorities, see [the roadmap](docs/roadmap.md).

## Project structure

The file tree:

```text
.
├── src/
│   ├── concerted_abduction/          # Main Python package
│   │   ├── types.py
│   │   ├── core/                     # Shared pipeline primitives
│   │   ├── data_utils/               # Synthetic data generation
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── data_generator.py
│   │   ├── fod/                      # Frame-of-discernment extraction
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── llm.py
│   │   ├── focal_set/                # Focal-set extraction
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── llm.py
│   │   ├── llm/                      # Language-model provider adapters
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   └── google.py
│   │   ├── utils/                    # Prompt loading and runner helpers
│   │   │   ├── run_utils.py
│   │   │   └── utils.py
│   │   ├── mass_functions/           # Placeholder for mass assignment
│   │   └── combiners/                # Placeholder for evidence combination
│   └── config/
│       ├── settings.py               # Loads environment and TOML configuration
│       └── default_config.toml       # Shared component defaults
├── scripts/
│   ├── generate_data.py              # Creates a timestamped synthetic dataset
│   └── run.py                        # Runs extraction on the newest dataset
├── prompts/                          # Versioned prompts for each LLM-backed component
├── data/synthetic/examples/          # Few-shot examples used for data generation
├── experiments/runs/                 # Generated pipeline results (Git-ignored)
├── notebooks/                        # Exploratory notebooks and quickstarts
├── docs/                             # Architecture, data model, ADRs, and proposals
├── tests/                            # Automated tests
├── integrations/                     # Unused provider placeholders
├── pyproject.toml                    # Package metadata, dependencies, and type-check config
└── config.toml                       # Optional local overrides; absent by default
```

Generated datasets go under `data/synthetic/generated/`, and pipeline results
go under `experiments/runs/`. Both are ignored by Git. The root-level
`integrations/` package contains unused placeholders; active provider adapters
belong in `src/concerted_abduction/llm/`.

## 1. Set up the project

You need:

- Python 3.13 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A Gemini API key for commands that call a language model

Install the project and its development dependencies:

```bash
uv sync
```

Create `.env` in the repository root when you need to make API calls:

```dotenv
GEMINI_API_KEY=your-key-here
```

Never commit `.env` or credentials. You can work on domain types, registries,
configuration, and unit tests without an API key.

Verify the local checkout without making an API call:

```bash
uv run python -c "import concerted_abduction; print('import succeeded')"
uv run basedpyright
```

## 2. Start with components

Most project features are implemented as **components**. A component is a
small class with one job—for example, an FoD extractor turns a sample into a
frame of discernment. Each component type has:

- A base class that defines the required method.
- One or more concrete implementations.
- A registry that gives each implementation a configuration name.

The FoD package is a good first example:

```text
src/concerted_abduction/fod/
├── base.py       # Defines what every extractor must do.
├── llm.py        # Implements extraction with a language model.
└── registry.py   # Maps names to extractor classes.
```

### Create a component implementation

Subclass the relevant base class, implement its required method, and register
the class under a unique name:

```python
@FodExtractorRegistry.register("my_fod_extractor")
class MyFodExtractor(FrameOfDiscernmentExtractor):
    def generate_frame(self, sample: DataSample) -> FodOutput:
        # Convert the sample into the output required by this component type.
        ...
```

The method signature is the component's contract. In this example, callers can
use any registered FoD extractor because every extractor accepts a `DataSample`
and returns a `FodOutput`.

### Construct and invoke a component directly

Direct construction is useful for prototypes and tests:

```python
extractor = MyFodExtractor()
result = extractor.generate_frame(sample)
```

Pass constructor dependencies explicitly. For example, the existing
`LanguageModelFodExtractor` receives a `LanguageModel` object.

### Construct a component from configuration

Runnable scripts select implementations by their registered names. A component
does not inherit configuration-based construction from
`FrameOfDiscernmentExtractor`: the developer must implement a `from_config()`
class method on each component that should support it.

The current runner passes a parsed `ComponentConfig` object to `from_config()`.
The method does not read or infer directly from TOML; its job is to validate
the settings it needs and construct the component from them.

If `ComponentConfig` does not represent the settings required by a new
component, defining another Pydantic model is only the first step. You must
also update the corresponding field on `ConcertedAbductionSettings` (or add
other configuration-dispatch logic) so Pydantic parses that TOML section into
the new model before the runner calls `from_config()`. Otherwise, the runner
continues to supply a `ComponentConfig`, and unsupported TOML fields may be
ignored.

> [!NOTE]
> **What is `ComponentConfig`?** It is the Pydantic model for one component's
> TOML section, including its registry `type`, output directory, optional LLM
> settings, prompt path, and examples path. Find its definition in
> [`src/config/settings.py`](src/config/settings.py), and see
> [`docs/configuration.md`](docs/configuration.md) for the corresponding TOML
> shape, configuration layering, and path-resolution behavior.

For example, a language-model-backed `MyFodExtractor` could use this skeleton:

```python
from typing import Self

from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.llm.registry import LanguageModelRegistry
from concerted_abduction.utils.utils import load_prompt
from config.settings import ComponentConfig


class MyFodExtractor(FrameOfDiscernmentExtractor):
    def __init__(self, language_model: LanguageModel) -> None:
        self.language_model = language_model

    @classmethod
    def from_config(cls, cfg: ComponentConfig) -> Self:
        if cfg.llm is None:
            raise ValueError(f"FoD extractor {cfg.type!r} requires an llm section")
        if cfg.prompt_path is None:
            raise ValueError(f"FoD extractor {cfg.type!r} requires prompt_path")

        language_model = LanguageModelRegistry.create(
            provider=cfg.llm.provider,
            model=cfg.llm.model_name,
            system_prompt=load_prompt(cfg.prompt_path),
        )
        return cls(language_model=language_model)

    # Implement generate_frame() as shown above.
```

Components without external dependencies can simply validate any settings
they use and return `cls()` from `from_config()`.

The runner then uses that method as follows:

```python
# Resolve the configured implementation by its registry name.
extractor_cls = FodExtractorRegistry._get(cfg.type)

# Construct it, including dependencies such as its language model and prompt.
extractor = extractor_cls.from_config(cfg)

# Invoke it through the common component interface.
result = extractor.generate_frame(sample)
```

If `from_config()` is absent, `scripts/run.py` raises `TypeError`. Direct
construction remains available and does not require this method.

Registration happens when Python imports the implementation module. If a new
component cannot be found, ensure its module is imported by the package's
`__init__.py` before the registry lookup occurs.

Once this flow is familiar, read [extending the project](docs/extending.md) for
the full checklist and [the component design ADR](docs/adr/0002-component-design-pattern.md)
for the rationale. The [architecture guide](docs/architecture.md) explains how
components form the larger research pipeline.

## 3. Run the current workflow

Both commands below call Gemini and may incur usage costs.

Generate a timestamped synthetic dataset:

```bash
uv run python scripts/generate_data.py
```

Then run FoD extraction against the newest generated dataset:

```bash
# Process one sample (the inexpensive default).
uv run python scripts/run.py

# Process a chosen number of samples or the entire dataset.
uv run python scripts/run.py --num-samples 5
uv run python scripts/run.py --all
```

Generated datasets are written below `data/synthetic/generated/`; extraction
results are written below `experiments/runs/`. Both locations are ignored by
Git. Each run includes metadata describing its inputs and configuration.

The defaults live in `src/config/default_config.toml`. To experiment without
changing shared defaults, create a repository-root `config.toml` containing
only your overrides. Settings are deep-merged with the defaults.

## 4. Try the component pattern

Open [the component quickstart notebook](notebooks/component_quickstart.ipynb)
with the project's Python environment and run it from top to bottom. It reads
`GEMINI_API_KEY` from the repository's `.env` file and makes two Gemini
requests, which may incur usage costs.

The notebook walks through one complete example:

1. Create a `DataSample`.
2. Implement the `FrameOfDiscernmentExtractor` interface with a `LanguageModel`
   dependency.
3. Register the implementation by name.
4. Construct and invoke it directly with an explicit `LanguageModel`.
5. Construct it through the registry and the project's TOML configuration.
6. Invoke it through the common interface and validate Gemini's structured
   output.

After it runs, change the extractor to ignore empty or duplicate responses and
rerun the final cells. This is a small way to practice changing component
behavior without changing its interface.
