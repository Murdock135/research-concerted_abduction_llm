# Roadmap / TODO

Mirrors the "Current TODO" section in CLAUDE.md, with more detail.

## Implemented

- [x] Synthetic dataset generation (`CommonInputDataGenerator`, Gemini + structured JSON schema output)
- [x] Typed dataset schema (`ModelOutput`, `DataSample`, `DataSet`)
- [x] LLM-based hypothesis extraction / Universe of Discourse construction (`LlmHypothesisExtractor`)
- [x] Registry pattern for pluggable components (`DataGeneratorRegistry`, `ExtractorRegistry`)
- [x] `config.toml`-driven configuration: per-component LLM selection, prompt paths, example paths, output directories (`src/config/settings.py`)

## Not yet implemented

- [ ] **Mass function assignment** (`src/concerted_abduction/mass_functions/`) — currently empty. Needs to take a model's response + the UoD and produce a confidence-weighted mass distribution over subsets of hypotheses.
- [ ] **Evidence combiners** (`src/concerted_abduction/combiners/`) — currently empty. Needs to implement Dempster's rule of combination over the per-model mass functions to produce a single reconciled belief distribution.
- [ ] **Structured UoD output** — `LlmHypothesisExtractor.create_uod` currently returns raw LLM text (`response.text`), not a typed/parseable structure. Mass function assignment will likely need a structured UoD (e.g. an explicit list/set of hypotheses) rather than free text.
- [ ] **End-to-end pipeline** — `scripts/pipeline_prototype.py` only runs data loading + hypothesis extraction today; it stops before mass functions/combination.
- [ ] **Environment variable loading helper** — clean up the discrepancy between the documented secrets location (`~/.secrets/.llm_apis`) and what `ENVSettings`/`ENV_PATH` in `src/config/settings.py` actually resolves to (`<project_root>/.env`) — see the note in [configuration.md](configuration.md).
- [ ] **Tests** — `tests/` is empty.
- [ ] **`integrations/`** (`gemini.py`, `langchain.py`, `openai.py`) — empty stubs, presumably for supporting additional/alternate LLM providers beyond the current direct `google-genai` SDK usage; not wired into any component yet.
- [ ] **`src/concerted_abduction/core/`** — empty package, purpose not yet defined.
- [ ] **CLI parameterization** — `scripts/generate_data.py`'s prompt (scenario count, domain, overlap matrix) is currently hardcoded in the script rather than configurable via CLI args or config.

---
That's the end of the reading sequence — back to [README.md](README.md), or see [refs.md](refs.md) for external references.
