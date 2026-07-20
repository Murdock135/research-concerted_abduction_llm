# Data Model

Defined in `src/concerted_abduction/types.py` as Pydantic models. This is the shared schema between data generation and hypothesis extraction.

## `ModelOutput`

One model's response within a scenario.

| field | type | description |
|---|---|---|
| `model_name` | `str` | Name of the model that generated this output (e.g. `"A"`, `"B"`, `"C"`) |
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
- `get_samples_by_model_name(model_name)` — all samples that include an output from a given model
- `convert_to_dataframe()` — flatten to a `pandas.DataFrame`, one row per `(sample, output)` pair (marked as untested — TODO in source)

## `OverlapMatrix`

Type alias: `npt.NDArray[np.int32]` — an n×n matrix where entry `(i, j)` represents the degree of overlap between model `i` and model `j`'s hypotheses for a scenario. Used as an input parameter when prompting the data generator (see the example prompt in [architecture.md](architecture.md)), not currently stored as a field on `DataSample` itself.

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
        { "model_name": "A", "response": "Based on your symptoms, here are some possibilities..." },
        { "model_name": "B", "response": "I understand you're experiencing several concerning symptoms..." },
        { "model_name": "C", "response": "ASSESSMENT SUMMARY\n\nPrimary hypothesis: ..." }
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
| `data/generated_dataset.json` | Output of `scripts/generate_data.py` (default `data_generator.output_dir` in config) |
| `data/synthetic/generated/common_input/v0.json` | An earlier/alternate generated dataset |
| `experiments/runs/<scenario_id>_uod.json` | Output of hypothesis extraction, one file per scenario, `{"uod": "<free text>"}` |

---
Next: [configuration.md](configuration.md) — how to control which LLM/prompt/examples each component uses.
