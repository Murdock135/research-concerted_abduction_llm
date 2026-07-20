# Contributing

This is early-stage research code (see [docs/roadmap.md](docs/roadmap.md) for what's implemented vs. planned). There's no CI, no enforced linter, and no test suite yet, so this document is mostly about keeping the codebase consistent with itself while that infrastructure doesn't exist — not a formal process.

## Setup

```bash
uv sync
```

Python ≥ 3.13 required. You'll need a `GEMINI_API_KEY` to run anything that calls the LLM — see [docs/configuration.md](docs/configuration.md) for where it's read from.

Read [docs/README.md](docs/README.md) before making non-trivial changes — it walks through the research idea, the pipeline stages, the data schema, and the config/registry pattern in order.

## Adding a new pipeline component

Data generation and hypothesis extraction are both implemented as **pluggable components**: an abstract base class + a name→class registry + a `config.toml` entry selecting which implementation runs. If you're adding a new data generator, extractor, or (once they exist) mass function / combiner, follow that existing pattern rather than special-casing your addition — see [docs/extending.md](docs/extending.md) for the concrete steps.

If you're implementing **mass function assignment** or **evidence combination** (currently empty packages, see [docs/roadmap.md](docs/roadmap.md)), set them up the same way: `base.py` with an ABC, `registry.py` with a registry class, a concrete implementation registered via decorator, and a corresponding section added to `ConcertedAbductionSettings` in `src/config/settings.py` + `src/config/default_config.toml`.

## Conventions

- **Types**: dataset/domain objects are Pydantic models in `src/concerted_abduction/types.py`. Extend this schema rather than passing around ad-hoc dicts.
- **Paths**: use `find_project_root()` / `load_prompt()` from `src/concerted_abduction/utils/utils.py` instead of hardcoding relative paths — scripts should work regardless of the caller's working directory.
- **Prompts**: keep prompt text in `prompts/`, loaded via `load_prompt()`, not inlined as Python string literals.
- **Config over hardcoding**: LLM choice, prompt path, examples path, and output directory for a component belong in `config.toml`/`default_config.toml` (via `ComponentConfig`), not hardcoded in the component itself.
- **Registries only register on import**: registration happens via decorator at import time. If you add a new implementation and `Registry.get()` can't find it, check it's actually imported (see the `__init__.py` files in `data_utils/` and `extractors/` for the pattern).

## Tests

`tests/` currently only contains a `.gitkeep`. There's no test runner configured yet — if you add the first test, you'll also need to add a test dependency (e.g. `pytest`) to `pyproject.toml`. Until then, verify changes by actually running the affected script(s) against real or synthetic data.

## Commits

Keep commit messages short and describe what changed in plain language (see `git log` for the existing style — it's informal, not Conventional Commits). No PR template or required review process exists; this has been a single-contributor repo so far.

## Secrets

Never commit API keys. `GEMINI_API_KEY` is read from an env file (see the note in [docs/configuration.md](docs/configuration.md) about exactly which path) — keep it out of version control.
