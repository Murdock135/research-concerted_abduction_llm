# Extending: the registry pattern

Both pluggable component types (data generators, FoD extractors) follow the same pattern: an abstract base class, a decorator-based registry, and lookup by string name from `config.toml`.

## Anatomy

Using data generators as the example (`src/concerted_abduction/data_utils/`):

- **`base.py`** — `DataGenerator(ABC)` with an abstract `generate_data(prompt: str) -> DataSet`.
- **`registry.py`** — `DataGeneratorRegistry`, a class holding a `{name: class}` dict with `register(name)` (class decorator), `get(name)`, and `list_generators()`.
- **`data_generator.py`** — concrete implementation, registered via decorator:

```python
@DataGeneratorRegistry.register("common_input")
class CommonInputDataGenerator(DataGenerator):
    def generate_data(self, prompt: str) -> DataSet:
        ...
```

`config.toml` then selects it by name:

```toml
[data_generator]
type = "common_input"
```

And calling code resolves the class dynamically:

```python
generator_cls = DataGeneratorRegistry.get(cfg.type)
generator = generator_cls(language_model=cfg.llm.model_name, examples_path=cfg.examples_path)
```

The same pattern applies to `src/concerted_abduction/fod/` (`FrameOfDiscernmentExtractor`, `FodExtractorRegistry`).

## Adding a new data generator

1. Create a class in `src/concerted_abduction/data_utils/` that subclasses `DataGenerator` and implements `generate_data(self, prompt: str) -> DataSet`.
2. Decorate it with `@DataGeneratorRegistry.register("your_name")`.
3. Make sure the module is imported somewhere on the import path before `DataGeneratorRegistry.get()` is called (registration happens at import/decoration time — an unimported module never registers).
4. Point `config.toml`'s `[data_generator] type = "your_name"` at it, plus any `llm`/`prompt_path`/`examples_path` it needs.

## Adding a new frame-of-discernment extractor

Same steps, but subclass `FrameOfDiscernmentExtractor` and implement `generate_frame(self, sample)`, then decorate it with `@FodExtractorRegistry.register("your_name")`.

## Mass functions and combiners (not yet started)

`src/concerted_abduction/mass_functions/` and `src/concerted_abduction/combiners/` are empty packages. When implementing them, following the same base-class + registry + `ComponentConfig` pattern used above would keep the pipeline consistent — a `mass_functions` and `combiners` section would need to be added to `ConcertedAbductionSettings` in `src/config/settings.py`, plus corresponding entries in `default_config.toml`.

---
Next: [project_structure.md](project_structure.md) — a full annotated file tree, for reference while you work.
