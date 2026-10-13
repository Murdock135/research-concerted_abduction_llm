# Extending: the registry pattern

The pluggable component types (data generators, FoD extractors, focal-set creators, BPA assigners, and combiners) follow the same pattern: an abstract base class, a decorator-based registry, and lookup by string name from `config.toml`.

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

## Adding a new focal-set creator

Subclass `FocalSetCreator`, implement `create_focal_sets(self, fod_output)`, and decorate the implementation with `@FocalSetRegistry.register("your_name")`. The result must be a `FocalSetOutput`; implementations should preserve source attribution and ensure every cited excerpt comes from its corresponding source text.

## Adding a BPA assigner

Subclass `BpaAssigner`, implement `assign_masses(fod_output, focal_set_output)`
returning `BpaOutput`, register with `BpaRegistry`, and provide a
`from_config(cfg)` constructor. Import the implementation in `bpa/__init__.py`
and select it under `[bpa]`.

## Adding a combiner

Subclass `Combiner` and implement `combine(bpa_assignments)` returning
`tuple[CombinedMasses, float]` (combined masses, then conflict mass). Register it
with `@CombinerRegistry.register("your_method")`, import it in
`combiners/__init__.py`, and set `[combiner] type = "your_method"`.
The runner constructs combiners without arguments. All pipeline analysis stages
must use the same `output_dir`. Keep method-specific arithmetic in the implementation.

---
Next: [project_structure.md](project_structure.md) — a full annotated file tree, for reference while you work.
