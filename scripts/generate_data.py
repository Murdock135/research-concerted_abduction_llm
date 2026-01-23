
import json
import os

from google import genai
from dotenv import load_dotenv

from concerted_abduction.data_generator.data_generator import DataGenerator
from concerted_abduction.utils.utils import find_project_root

MODEL = "gemini-2.5-flash"

def main():
    """Main execution function for the pipeline prototype."""
    env_path = "~/.secrets/.llm_apis"
    load_dotenv(dotenv_path=os.path.expanduser(env_path))

    print("ENVIRONEMENT VARIABLES:")
    print("GEMINI_API_KEY =", os.getenv("GEMINI_API_KEY"))
    
    if not os.getenv("GEMINI_API_KEY"):
        raise EnvironmentError("GEMINI_API_KEY not found in environment variables.")
        
    # Initialize the data generator
    generator = DataGenerator(language_model=MODEL)

    # Example prompt for generating data
    prompt = "Generate 5 data samples in a medical diagnosis scenario for 3 models with the following overlap matrix: [[1.0, 0.5, 0.2], [0.5, 1.0, 0.3], [0.2, 0.3, 1.0]]"
    dataset = generator.generate_data(prompt=prompt)
    print("Generated Dataset:\n", dataset)

    # Dump the generated dataset to a JSON file
    output_path = find_project_root(__file__) / "data" / "generated_dataset.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset.model_dump(), f, ensure_ascii=False, indent=4)
    print(f"Generated dataset saved to {output_path}")

if __name__ == "__main__":
    main()
