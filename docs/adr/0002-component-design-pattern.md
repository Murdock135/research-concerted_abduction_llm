- **Date:** 2023-08-23
- **Status:** Accepted

# TL;DR

Components use a **strategy/plugin pattern**: each component type defines an
abstract interface, while concrete implementations can be selected at runtime.
Implementations register themselves by name through a decorator-based
**registry**, which also acts as a simple factory.

Components can be constructed in two ways:

1. Directly, for example `LlmHypothesisExtractor(language_model)`.
2. From TOML configuration, by looking up the configured implementation and
   asking it to construct itself:

```python
# Look up the registered component class using the name from configuration.
extractor_cls = ExtractorRegistry._get(cfg.type)

# Let the selected implementation resolve its dependencies and create itself.
extractor = extractor_cls.from_config(cfg)
```

Here, `cfg.type` is the implementation's registered name. `from_config()` is a
configuration adapter implemented by components that support config-driven
construction; it resolves dependencies such as the language-model provider,
model, and prompt. Registration occurs when the implementation's module is
imported.

## Why isn't `from_config()` part of the abstract interface?

Making `from_config()` abstract would require every component to implement it,
including components intended only for direct construction or rapid
prototyping. Configuration support is therefore an optional adapter rather than
part of the component's core contract. Code that constructs components from
configuration must check that the selected implementation provides a callable
`from_config()` method and report a clear error if it does not.
