# Data Model

Defined in `src/concerted_abduction/types.py` as Pydantic models. This is the shared schema between data generation and hypothesis extraction.

## `ModelOutput`

One model's response within a scenario.

| field | type | description |
|---|---|---|
| `source` | `str` | Name of the source that generated this output |
| `response` | `str` | The model's free-text response |

## `DataSample`

One scenario: a single input message and the set of model responses to it.

| field | type | description |
|---|---|---|
| `scenario_id` | `str` | Unique identifier for the scenario |
| `created_at` | `str` | Creation timestamp, format `YYYY-MM-DD` |
| `input_message` | `str` | The input given to all models (e.g. a patient's symptom description) |
| `outputs` | `list[ModelOutput]` | One entry per model that responded to `input_message` |

## `DataSet`

A collection of samples, with a few convenience methods:

- `add_sample(sample)` — append a `DataSample`
- `get_sample_by_id(scenario_id)` — lookup by id, or `None`
- `get_samples_by_source(source)` — all samples that include an output from a given source
- `convert_to_dataframe()` — flatten to a `pandas.DataFrame`, one row per `(sample, output)` pair (marked as untested — TODO in source)

## Focal-set output

`FocalSetOutput` groups results by source through `SourceFocalSets`. Each
`FocalSet` contains:

| field | type | description |
|---|---|---|
| `hypotheses` | `list[str]` | A non-empty subset of exact labels from the frame of discernment |
| `justification` | `str` | Why that source supports the subset |
| `citations` | `list[str]` | Non-empty verbatim excerpts from the corresponding source text |

`FocalSetOutput.validation_errors` records semantic problems found after
generation, including invalid frame membership, source coverage, and citations.
These checks do not discard the generated focal sets; the runner saves the
output and emits a warning so failed experiments remain inspectable.

## Example JSON

From `data/synthetic/examples/common_input/v0.json` (used as a few-shot example for data generation):

```json
{
  "samples": [
    {
      "id": "1",
      "created_at": "2025-11-24",
      "input_message": "I've been having this dull headache for about two weeks now...",
      "outputs": [
        { "source": "A", "response": "Based on your symptoms, here are some possibilities..." },
        { "source": "B", "response": "I understand you're experiencing several concerning symptoms..." },
        { "source": "C", "response": "ASSESSMENT SUMMARY\n\nPrimary hypothesis: ..." }
      ]
    }
  ]
}
```

Note: the example file uses `id`, but the live `DataSample` schema field is `scenario_id`.

## Where data lives

| path | contents |
|---|---|
| `data/synthetic/examples/common_input/v0.json` | Few-shot examples fed to the data generator's prompt |
| `<data_generator.output_dir>/<run>/generated_dataset.json` | Output of `scripts/generate_data.py` |
| `data/synthetic/generated/common_input/v0.json` | An earlier/alternate generated dataset |
| `<fod_extractor.output_dir>/<run>/<scenario_id>/frame.json` | Structured FoD-extraction output, one file per scenario |
| `<fod_extractor.output_dir>/<run>/<scenario_id>/focal_sets.json` | Cited focal sets grouped by source, one file per scenario |
| `<bpa.output_dir>/<run>/<scenario_id>/bpa.json` | Validated per-source mass assignments |
| `<combiner.output_dir>/<run>/<scenario_id>/combined.json` | Combined masses and conflict |
| `<combiner.output_dir>/<run>/<scenario_id>/error.json` | Stage, error type, and message for a failed scenario |
| `<combiner.output_dir>/<run>/summary.json` | Batch outcomes and counts |

## BPA and combined evidence

`FocalSetMass` contains `hypotheses`, `mass`, and `justification`. `SourceBpa`
groups masses by source and validates duplicate subsets and a total of one
(tolerance `1e-6`). `BpaOutput` contains unique source BPAs.

`CombinedMasses` contains `combined_masses`, a list of `CombinedMass` entries.
Dempster populates each entry's `focal_set` and `combined_mass`, and returns
conflict separately as the second tuple member. The runner writes both to JSON:

```json
{
  "combined_masses": [{"focal_set": ["hypothesis"], "combined_mass": 1.0, "k": null}],
  "conflict": 0.0
}
```

The existing `CombinedMass.k` field is an alternative mass field; the Dempster
result uses `combined_mass`. Conflict is saved once at the top level.

---
Next: [configuration.md](configuration.md) — how to control which LLM/prompt/examples each component uses.
