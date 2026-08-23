- **Date:** 2023-08-23
- **Status:** Accepted

# TL;DR

Language-model providers use an **adapter/strategy pattern**. The
`LanguageModel` abstract base class defines the provider-independent contract,
and each provider implements that contract using its own SDK. Application
components depend on `LanguageModel`, not on a provider-specific client.

Providers register themselves by name through a decorator-based **registry**,
which acts as a factory when configuration selects a provider:

```python
# Look up the provider configured for this component and create its adapter.
language_model = LanguageModelRegistry.create(
    provider=cfg.llm.provider,
    model=cfg.llm.model_name,
    system_prompt=load_prompt(cfg.prompt_path),
)

# Invoke the provider through the shared interface and validate structured output.
response = language_model.generate(prompt, output_schema=SomeSchema)
```

Here, `cfg.llm.provider` is the provider's registered name, such as
`"google_genai"`. Importing a provider module runs its registration decorator.
`generate()` returns plain text by default; when given a Pydantic
`output_schema`, it requests structured output and returns a validated model.

## Why put provider SDKs behind `LanguageModel`?

Provider SDKs differ in client construction, request options, structured-output
support, response parsing, and error types. Keeping those details inside an
adapter gives components one stable interface and allows providers to be
changed through configuration without rewriting component logic.

## Why use a registry instead of conditional provider selection?

A registry keeps provider selection extensible. Adding a provider requires a
new `LanguageModel` implementation and a registration decorator, rather than
adding another branch to a central factory. Built-in provider modules must be
imported before lookup so their decorators can run.
