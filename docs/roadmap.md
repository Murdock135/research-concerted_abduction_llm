# Roadmap / TODO

Mirrors the "Current TODO" section in CLAUDE.md, with more detail.

## Implemented

- [x] Synthetic dataset generation (`CommonInputDataGenerator`, Gemini + structured JSON schema output)
- [x] Typed dataset schema (`ModelOutput`, `DataSample`, `DataSet`)
- [x] LLM-based frame-of-discernment extraction (`LanguageModelFodExtractor`)
- [x] Structured frame output (`FrameOfDiscernment`, schema-constrained Gemini response)
- [x] Registry pattern for pluggable components (`DataGeneratorRegistry`, `FodExtractorRegistry`)
- [x] `config.toml`-driven configuration: per-component LLM selection, prompt paths, example paths, output directories (`src/config/settings.py`)

## Not yet implemented

- [ ] **Mass function assignment** (`src/concerted_abduction/mass_functions/`) — currently empty. Needs to take a model's response + the UoD and produce a confidence-weighted mass distribution over subsets of hypotheses.
- [ ] **Evidence combiners** (`src/concerted_abduction/combiners/`) — currently empty. Needs to implement Dempster's rule of combination over the per-model mass functions to produce a single reconciled belief distribution.
- [ ] **End-to-end pipeline** — `scripts/pipeline_prototype.py` only runs data loading + hypothesis extraction today; it stops before mass functions/combination.
- [ ] **Tests** — `tests/` is empty.
- [ ] **`integrations/`** (`gemini.py`, `langchain.py`, `openai.py`) — empty stubs, presumably for supporting additional/alternate LLM providers beyond the current direct `google-genai` SDK usage; not wired into any component yet.
- [ ] **`src/concerted_abduction/core/`** — empty package, purpose not yet defined.
- [ ] **CLI parameterization** — `scripts/generate_data.py`'s prompt (scenario count, domain, overlap matrix) is currently hardcoded in the script rather than configurable via CLI args or config.

---
That's the end of the reading sequence — back to [README.md](README.md), or see [refs.md](refs.md) for external references.
