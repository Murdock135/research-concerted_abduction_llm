# Roadmap / TODO

Current implementation status and remaining research work.

## Implemented

- [x] Synthetic dataset generation (`CommonInputDataGenerator`, Gemini + structured JSON schema output)
- [x] Typed dataset schema (`ModelOutput`, `DataSample`, `DataSet`)
- [x] LLM-based frame-of-discernment extraction (`LanguageModelFodExtractor`)
- [x] Structured frame output (`FrameOfDiscernment`, schema-constrained Gemini response)
- [x] LLM-based focal-set creation with cited source evidence (`LanguageModelFocalSetCreator`)
- [x] Registry pattern for pluggable components (`DataGeneratorRegistry`, `FodExtractorRegistry`, `FocalSetRegistry`)
- [x] `config.toml`-driven configuration: per-component LLM selection, prompt paths, example paths, output directories (`src/config/settings.py`)
- [x] Source BPA assignment (`bpa/`) with per-source distribution validation
- [x] Pluggable evidence combination (`combiners/`), default Dempster
- [x] Complete runner through combined masses, with per-scenario failure isolation
- [x] Combiner arithmetic tests and runner integration tests, including total conflict

## Remaining research work

- [ ] Evaluate frame extraction, focal-set support, and BPA assignment against reference data.
- [ ] Evaluate BPA calibration and the effect of related evidence sources.
- [ ] Compare combination methods and downstream decision rules if required by the study.

## Optional infrastructure work

- [ ] **`integrations/`** (`gemini.py`, `langchain.py`, `openai.py`) — empty stubs, presumably for supporting additional/alternate LLM providers beyond the current direct `google-genai` SDK usage; not wired into any component yet.
- [ ] **`src/concerted_abduction/core/`** — empty package, purpose not yet defined.
- [ ] **CLI parameterization** — `scripts/generate_data.py`'s prompt (scenario count, domain, overlap matrix) is currently hardcoded in the script rather than configurable via CLI args or config.

---
That's the end of the reading sequence — back to [README.md](README.md), or see [refs.md](refs.md) for external references.
