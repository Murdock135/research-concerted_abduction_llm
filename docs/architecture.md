# Architecture

## Pipeline stages

```
 1. Data generation   2. FoD extraction   3. Focal sets    4. Mass function   5. Evidence
    (implemented)        (implemented)       (implemented)     assignment         combination
                                                               (implemented)      (implemented)

 data_utils/        -> fod/              -> focal_set/     -> bpa/            -> combiners/

 data/.../<run>/generated_dataset.json   experiments/runs/<run>/<scenario_id>/frame.json
```

Each stage is defined as an abstract **component** (a base class + a package) with one or more concrete, **pluggable implementations**, looked up by name through a **registry** at runtime (see [extending.md](extending.md)). Which implementation, LLM, prompt file, and example file each component uses for a given run is controlled by `config.toml` (see [configuration.md](configuration.md)) — the descriptions below name the implementation currently registered as the default for each stage, not a fixed part of the stage itself.

## 1. Data generation

Package: `src/concerted_abduction/data_utils/`. Base class: `DataGenerator` (`generate_data(prompt: str) -> DataSet`). Registry: `DataGeneratorRegistry`.

Default implementation — `CommonInputDataGenerator` (`data_generator.py`), registered as `"common_input"`:

- Loads a system prompt (`prompts/data_generators/common_input/v0.txt`) and a set of few-shot example scenarios (`data/synthetic/examples/common_input/v0.json`), and appends the examples to the prompt.
- Calls the Gemini API with `response_mime_type="application/json"` and `response_json_schema=DataSet.model_json_schema()`, so the model is constrained to emit valid `DataSet` JSON directly.
- Given a natural-language instruction (e.g. "Generate 5 data samples in a medical diagnosis scenario for 3 models with overlap matrix [...]"), it returns a `DataSet` of synthetic scenarios where 3 named models ("A", "B", "C") each give a differentiated response to the same input.

Driven by `scripts/generate_data.py`, which resolves whichever generator is configured and writes the result to a timestamped directory under the configured output directory.

## 2. Frame-of-discernment extraction

Package: `src/concerted_abduction/fod/`. Base class: `FrameOfDiscernmentExtractor` (`generate_frame(sample)`). Registry: `FodExtractorRegistry`.

Default implementation — `LanguageModelFodExtractor` (`llm.py`), registered as `"language_model_fod_extractor"`:

- Takes the list of model responses for one scenario (the `outputs` from a `DataSample`) and asks Gemini to synthesize a single **Universe of Discourse (UoD)** — the combined set of hypotheses implied across all the model outputs, since each model's response only covers a fractional piece of it.
- Constrains Gemini to return a typed `FrameOfDiscernment` containing the elementary hypotheses.

Driven by `scripts/run.py`, which loads the latest generated dataset, resolves whichever extractor is configured, and passes each extracted frame to the focal-set stage.

## 3. Focal-set creation

Package: `src/concerted_abduction/focal_set/`. Base class: `FocalSetCreator` (`create_focal_sets(fod_output)`). Registry: `FocalSetRegistry`.

Default implementation — `LanguageModelFocalSetCreator` (`llm.py`), registered as `"language_model_focal_set_creator"`:

- Accepts an `FodOutput`, including its source-response mapping and frame of discernment.
- Produces focal sets grouped by source. Each focal set contains one or more exact frame labels, a justification, and one or more verbatim excerpts from that source's text.
- Checks that all input sources appear exactly once, every hypothesis belongs to the frame, and every citation occurs verbatim in the corresponding source text. Failures are recorded in `validation_errors` so experimental output is preserved for inspection.
- Is configured under `[focal_set]` and invoked after FoD extraction by `scripts/run.py`.

The runner writes `<scenario_id>/frame.json` and
`<scenario_id>/focal_sets.json` into a scenario-specific folder within the timestamped run directory. The `fod_extractor`, `focal_set`, `bpa`, and `combiner` output directories
must therefore match.

## 4. Mass function assignment

Package: `src/concerted_abduction/bpa/`. Base class: `BpaAssigner`.
Registry: `BpaRegistry`. Default implementation: `LanguageModelBpaAssigner`.

The assigner loops over the source-response mapping in `FodOutput`, making one
LLM call per source. Each request contains only that source's response and focal
sets, plus the shared frame. Empty or out-of-frame upstream groups are excluded;
citation diagnostics do not block assignment.

The LLM returns `SourceMassResponse`, a `masses` list of `FocalSetMass` entries
(`hypotheses`, `mass`, and `justification`). Python checks that each returned subset
is a supplied focal set for that source or the full frame. It then supplies the
source identifier when constructing `SourceBpa` and collects these objects into
`BpaOutput`. Custom BPA prompts must follow this response contract.

Masses must be finite numbers in [0, 1], with no duplicate subsets, and sum to one
per source (tolerance `1e-6`). Omitted subsets have zero mass. A source without
valid focal sets can receive only full ignorance. Invalid outputs raise errors;
Python does not normalize masses or automatically retry failed calls. The default
prompt is `prompts/bpa/v0.txt`.

## 5. Evidence combination

Package: `src/concerted_abduction/combiners/`. Base class: `Combiner`.
Registry: `CombinerRegistry`. Default: `DempsterCombination` (`"Dempster"`).

The contract is `combine(BpaOutput) -> tuple[CombinedMasses, float]`: normalized
combined masses followed by conflict mass. Dempster converts each source to a
set-keyed mass mapping, corrects source totals within BPA rounding tolerance,
reduces unnormalized intersections, and normalizes once at the end. Composite
focal sets are preserved. With three sources, discarded conflict increments are
added from the unnormalized reduction. Exact total conflict raises `ValueError`.

The runner constructs the registered combiner without arguments, invokes it after
BPA assignment, and writes `<scenario_id>/combined.json` with `combined_masses`
and `conflict`. The selected method is stored in run metadata. It makes no LLM calls.

Each stage's artifact is saved immediately. Ordinary scenario failures produce
`<scenario_id>/error.json`; subsequent scenarios continue. `summary.json` records
outcomes and counts. Setup failures stop the run, and any scenario failure yields
exit status 1 after the batch finishes. These masses remain research outputs;
no diagnosis ranking or generated final answer is added.

## Shared building blocks

- **`src/concerted_abduction/types.py`** — the Pydantic dataset schema shared by generation and extraction. See [data_model.md](data_model.md).
- **`src/concerted_abduction/utils/utils.py`** — `find_project_root()` (walks up from a file to the directory containing `.git`) and `load_prompt()` (reads a prompt file as text). Used throughout to resolve paths relative to the repo root regardless of where a script is invoked from.
- **`src/config/settings.py`** — TOML + env-driven configuration, see [configuration.md](configuration.md).
- **Registries** (`DataGeneratorRegistry`, `FodExtractorRegistry`, `FocalSetRegistry`, `BpaRegistry`, `CombinerRegistry`) — name → class lookup so `config.toml` can select an implementation by string. See [extending.md](extending.md).

## Not currently used

- `integrations/` (repo root, not under `src/`) — `gemini.py`, `langchain.py`, `openai.py` — all empty stub files. Not imported anywhere yet; presumably placeholders for future non-Gemini provider support.
- `src/concerted_abduction/core/` — empty package.
- `notebooks/scratch_gemini_api.ipynb` — scratch notebook, not part of the pipeline.

---
Next: [data_model.md](data_model.md) — the schema these stages pass between each other.
