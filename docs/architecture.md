# Architecture

## Pipeline stages

```
 1. Data generation       2. Hypothesis extraction     3. Mass function        4. Evidence
    (implemented)            (implemented)                assignment              combination
                                                            (NOT implemented)       (NOT implemented)

 data_utils/           ->  extractors/               ->  mass_functions/      ->  combiners/

 data/.../<run>/generated_dataset.json   experiments/runs/<run>/*_frame.json
```

Each stage is defined as an abstract **component** (a base class + a package) with one or more concrete, **pluggable implementations**, looked up by name through a **registry** at runtime (see [extending.md](extending.md)). Which implementation, LLM, prompt file, and example file each component uses for a given run is controlled by `config.toml` (see [configuration.md](configuration.md)) — the descriptions below name the implementation currently registered as the default for each stage, not a fixed part of the stage itself.

## 1. Data generation

Package: `src/concerted_abduction/data_utils/`. Base class: `DataGenerator` (`generate_data(prompt: str) -> DataSet`). Registry: `DataGeneratorRegistry`.

Default implementation — `CommonInputDataGenerator` (`data_generator.py`), registered as `"common_input"`:

- Loads a system prompt (`prompts/data_generators/common_input/v0.txt`) and a set of few-shot example scenarios (`data/synthetic/examples/common_input/v0.json`), and appends the examples to the prompt.
- Calls the Gemini API with `response_mime_type="application/json"` and `response_json_schema=DataSet.model_json_schema()`, so the model is constrained to emit valid `DataSet` JSON directly.
- Given a natural-language instruction (e.g. "Generate 5 data samples in a medical diagnosis scenario for 3 models with overlap matrix [...]"), it returns a `DataSet` of synthetic scenarios where 3 named models ("A", "B", "C") each give a differentiated response to the same input.

Driven by `scripts/generate_data.py`, which resolves whichever generator is configured and writes the result to a timestamped directory under the configured output directory.

## 2. Hypothesis extraction

Package: `src/concerted_abduction/extractors/`. Base class: `HypothesisExtractor` (`generate_frame(sample)`). Registry: `ExtractorRegistry`.

Default implementation — `LlmHypothesisExtractor` (`llm.py`), registered as `"llm_hypothesis_extractor"`:

- Takes the list of model responses for one scenario (the `outputs` from a `DataSample`) and asks Gemini to synthesize a single **Universe of Discourse (UoD)** — the combined set of hypotheses implied across all the model outputs, since each model's response only covers a fractional piece of it.
- Constrains Gemini to return a typed `FrameOfDiscernment` containing the elementary hypotheses.

Driven by `scripts/pipeline_prototype.py`, which loads the latest generated dataset, resolves whichever extractor is configured, extracts a frame per sample, and writes each one to a timestamped run directory as `<scenario_id>_frame.json`.

## 3. Mass function assignment (planned)

Package: `src/concerted_abduction/mass_functions/` — currently empty, no base class or registry yet.

Will assign a mass function per model: given a model's response and the UoD, distribute belief mass across subsets of the UoD's hypotheses (confidence-based, per the CLAUDE.md TODO). Expected to follow the same base-class + registry pattern as the stages above (see [extending.md](extending.md)).

## 4. Evidence combination (planned)

Package: `src/concerted_abduction/combiners/` — currently empty, no base class or registry yet.

Will combine per-model mass functions into a single belief distribution using Dempster's rule of combination. Expected to follow the same base-class + registry pattern as the stages above.

## Shared building blocks

- **`src/concerted_abduction/types.py`** — the Pydantic dataset schema shared by generation and extraction. See [data_model.md](data_model.md).
- **`src/concerted_abduction/utils/utils.py`** — `find_project_root()` (walks up from a file to the directory containing `.git`) and `load_prompt()` (reads a prompt file as text). Used throughout to resolve paths relative to the repo root regardless of where a script is invoked from.
- **`src/config/settings.py`** — TOML + env-driven configuration, see [configuration.md](configuration.md).
- **Registries** (`DataGeneratorRegistry`, `ExtractorRegistry`) — name → class lookup so `config.toml` can select an implementation by string. See [extending.md](extending.md).

## Not currently used

- `integrations/` (repo root, not under `src/`) — `gemini.py`, `langchain.py`, `openai.py` — all empty stub files. Not imported anywhere yet; presumably placeholders for future non-Gemini provider support.
- `src/concerted_abduction/core/` — empty package.
- `notebooks/scratch_gemini_api.ipynb` — scratch notebook, not part of the pipeline.

---
Next: [data_model.md](data_model.md) — the schema these stages pass between each other.
