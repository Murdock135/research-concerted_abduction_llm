# Extending: the registry pattern

The pluggable component types (data generators, FoD extractors, and focal-set creators) follow the same pattern: an abstract base class, a decorator-based registry, and lookup by string name from `config.toml`.

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

Subclass `BpaAssigner` in `bpa/`, implement `assign_masses(fod_output,
focal_set_output)`, register with `BpaRegistry`, and select it through `[bpa]`.

## Adding an evidence combiner

1. Subclass `EvidenceCombiner` in `combiners/`.
2. Implement `from_config(cls, cfg: CombinerConfig)` and
   `combine(self, bpa_output: BpaOutput, frame: FrameOfDiscernment) -> CombinedEvidence`.
3. Decorate the implementation with `@CombinerRegistry.register("your_name")`.
4. Import its module in `combiners/__init__.py` so registration occurs.
5. Set `[combiner] type = "your_name"` in `config.toml`.

There is no fixed limit on registered methods. Each implementation validates its
inputs and returns normalized combined masses over the explicit frame, with source
identifiers and a method name. `CombinedMass.hypotheses=[]` can represent retained
conflict. `conflict_mass` is optional; document its meaning for each method and put
additional JSON-compatible diagnostics in `diagnostics`. Extend configuration as
needed for method-specific options. The runner uses only the abstract interface.

The base class supplies `_prepare_inputs(bpa_output, frame)` for shared validation
and conversion to set-keyed mass mappings. It returns `PreparedEvidence` containing
the copied frame, source identifiers, distributions, and original mass totals.
It preserves masses, including zero entries; normalization is an explicit decision
for each method. `MassDistribution` is the shared type alias in `combiners/types.py`.

Use `_build_result(frame=..., sources=..., masses=..., combiner=...,
diagnostics=..., conflict_mass=...)` to order subsets consistently and validate the
output contract. This helper preserves empty-set mass and does not normalize or
clip values. The base class imposes no source-combination order. Dempster alone
owns `_combine_pair`, source normalization, sequential processing, numerical
thresholds, and cumulative conflict accounting.

---
Next: [project_structure.md](project_structure.md) — a full annotated file tree, for reference while you work.
