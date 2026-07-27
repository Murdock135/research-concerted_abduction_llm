'''
Generate synthetic data for the concerted abduction project using a language model. This script initializes the data generator, creates a prompt for generating data, and saves the generated dataset to a JSON file.
'''
import json

from concerted_abduction.data_utils import DataGeneratorRegistry
from concerted_abduction.utils.run_utils import make_run_dir, save_run_metadata
from config.settings import ENVSettings, ConcertedAbductionSettings

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

    # Example prompt for generating data
    prompt = "Generate 5 data samples in a medical diagnosis scenario for 3 models with the following overlap matrix: [[1.0, 0.5, 0.2], [0.5, 1.0, 0.3], [0.2, 0.3, 1.0]]"
    dataset = generator.generate_data(prompt=prompt)
    print("Generated Dataset:\n", dataset)

    # Dump the generated dataset to a JSON file
    run_dir = make_run_dir(cfg.output_dir)
    output_path = run_dir / "generated_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=4)
    print(f"Generated dataset saved to {output_path}")

    save_run_metadata(
        run_dir,
        generator_type=cfg.type,
        examples_path=str(cfg.examples_path),
        model=cfg.llm.model_name,
        prompt=prompt,
    )

if __name__ == "__main__":
    main()
