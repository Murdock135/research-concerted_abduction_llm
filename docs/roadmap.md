# Roadmap / TODO

Mirrors the "Current TODO" section in CLAUDE.md, with more detail.

## Implemented

- [x] Per-source BPA assignment (`LanguageModelBpaAssigner`) and runner integration
- [x] Pluggable evidence combination (`EvidenceCombiner`, `CombinerRegistry`)
- [x] Deterministic normalized Dempster combination with conflict diagnostics
- [x] Runner integration and per-scenario combined artifacts
- [x] Focused combiner tests and mocked runner coverage

- [x] Synthetic dataset generation (`CommonInputDataGenerator`, Gemini + structured JSON schema output)
- [x] Typed dataset schema (`ModelOutput`, `DataSample`, `DataSet`)
- [x] LLM-based frame-of-discernment extraction (`LanguageModelFodExtractor`)
- [x] Structured frame output (`FrameOfDiscernment`, schema-constrained Gemini response)
- [x] LLM-based focal-set creation with cited source evidence (`LanguageModelFocalSetCreator`)
- [x] Registry pattern for pluggable components (`DataGeneratorRegistry`, `FodExtractorRegistry`, `FocalSetRegistry`)
- [x] `config.toml`-driven configuration: per-component LLM selection, prompt paths, example paths, output directories (`src/config/settings.py`)

## Not yet implemented

- [ ] **Additional combination methods** — register new `EvidenceCombiner` implementations as required by experiments.
- [ ] **Comprehensive tests** — focused stage tests and mocked runner coverage exist; live LLM pipeline execution is not covered by automated tests.
- [ ] **`integrations/`** (`gemini.py`, `langchain.py`, `openai.py`) — empty stubs, presumably for supporting additional/alternate LLM providers beyond the current direct `google-genai` SDK usage; not wired into any component yet.
- [ ] **`src/concerted_abduction/core/`** — empty package, purpose not yet defined.
- [ ] **CLI parameterization** — `scripts/generate_data.py`'s prompt (scenario count, domain, overlap matrix) is currently hardcoded in the script rather than configurable via CLI args or config.

---
That's the end of the reading sequence — back to [README.md](README.md), or see [refs.md](refs.md) for external references.
