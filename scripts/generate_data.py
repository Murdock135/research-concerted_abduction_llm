'''
Generate synthetic data for the concerted abduction project using a language model. This script initializes the data generator, uses the generation prompt below, and saves the generated dataset to a JSON file.
'''
import json

from concerted_abduction.data_utils import DataGeneratorRegistry
from concerted_abduction.utils.run_utils import make_run_dir, save_run_metadata
from config.settings import ENVSettings, ConcertedAbductionSettings


GENERATION_PROMPT = """Generate many (10-20) synthetic medical diagnosis data samples. Generate samples with
varying degrees of overlap so we can test a data fusion or evidence fusion pipeline downstream. For each 
degree of overlap, generate a few samples. Make sure the dataset has a balanced number of each type of 
sample.

Include Zadeh's classic counterexample as the remaining sample, with id
"zadeh_classic". This sample must have exactly 2 sources, Doctor A and Doctor B,
rather than 3 models.
Use the mutually exclusive, exhaustive frame {meningitis, concussion, brain tumor}.
Doctor A assigns basic belief masses m({meningitis}) = 0.99 and
m({brain tumor}) = 0.01. Doctor B assigns m({concussion}) = 0.99 and
m({brain tumor}) = 0.01. All other masses are zero, including mass on the full
frame. State these exact masses explicitly in each doctor's response as supplied
synthetic belief assignments, so they can be recovered without inferring them
from qualitative confidence. Do not add diagnoses, uncertainty mass, or a third
source to this sample.

This sample is intended to illustrate the counterintuitive effect of normalized
Dempster combination under nearly total conflict: K = 0.9999, the unnormalized
mass on {brain tumor} is 0.0001, and normalization yields m({brain tumor}) = 1,
even though both sources initially assign it only 0.01. Use this as the design
target; keep the two source responses separate and do not replace their beliefs
with the combined result. Return the usual dataset schema.
"""

def main():
    env = ENVSettings()
    if not env.gemini_api_key:
        raise EnvironmentError("GEMINI_API_KEY not found in environment variables.")

    cfg = ConcertedAbductionSettings().data_generator
    if cfg.llm is None:
        raise ValueError(f"data_generator config of type '{cfg.type}' requires an 'llm' section")

    # Initialize the data generator configured for this run
    generator_cls = DataGeneratorRegistry.get(cfg.type)
    generator = generator_cls(
        language_model=cfg.llm.model_name,
        examples_path=cfg.examples_path,
    )

    dataset = generator.generate_data(prompt=GENERATION_PROMPT)

    # Dump the generated dataset to a JSON file
    run_dir = make_run_dir(cfg.output_dir)
    output_path = run_dir / "generated_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=4)
    print(f"Generated dataset saved to {output_path}")

    if dataset.report:
        print(dataset.report)

    save_run_metadata(
        run_dir,
        generator_type=cfg.type,
        examples_path=str(cfg.examples_path),
        model=cfg.llm.model_name,
        prompt=GENERATION_PROMPT,
    )

if __name__ == "__main__":
    main()
