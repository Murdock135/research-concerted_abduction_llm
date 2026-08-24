# Roadmap / TODO

Mirrors the "Current TODO" section in CLAUDE.md, with more detail.

## Implemented

- [x] Synthetic dataset generation (`CommonInputDataGenerator`, Gemini + structured JSON schema output)
- [x] Typed dataset schema (`ModelOutput`, `DataSample`, `DataSet`)
- [x] LLM-based frame-of-discernment extraction (`LanguageModelFodExtractor`)
- [x] Structured frame output (`FrameOfDiscernment`, schema-constrained Gemini response)
- [x] LLM-based focal-set creation with cited source evidence (`LanguageModelFocalSetCreator`)
- [x] Registry pattern for pluggable components (`DataGeneratorRegistry`, `FodExtractorRegistry`, `FocalSetRegistry`)
- [x] `config.toml`-driven configuration: per-component LLM selection, prompt paths, example paths, output directories (`src/config/settings.py`)

## Not yet implemented

- [ ] **Mass function assignment** (`src/concerted_abduction/mass_functions/`) — currently empty. Needs to take a model's response + the UoD and produce a confidence-weighted mass distribution over subsets of hypotheses.
- [ ] **Evidence combiners** (`src/concerted_abduction/combiners/`) — currently empty. Needs to implement Dempster's rule of combination over the per-model mass functions to produce a single reconciled belief distribution.
- [ ] **End-to-end pipeline** — `scripts/run.py` runs FoD extraction and focal-set creation, but does not yet invoke mass assignment or combination.
- [ ] **Comprehensive tests** — focused focal-set unit tests exist, but the complete pipeline is not covered.
- [ ] **`integrations/`** (`gemini.py`, `langchain.py`, `openai.py`) — empty stubs, presumably for supporting additional/alternate LLM providers beyond the current direct `google-genai` SDK usage; not wired into any component yet.
- [ ] **`src/concerted_abduction/core/`** — empty package, purpose not yet defined.
- [ ] **CLI parameterization** — `scripts/generate_data.py`'s prompt (scenario count, domain, overlap matrix) is currently hardcoded in the script rather than configurable via CLI args or config.

---
That's the end of the reading sequence — back to [README.md](README.md), or see [refs.md](refs.md) for external references.
