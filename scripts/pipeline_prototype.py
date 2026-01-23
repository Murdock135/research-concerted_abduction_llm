"""Monolithic prototype implementing the full Concerted Abduction pipeline.

This file contains a single-file implementation of:
- Hypothesis extraction (LLM-based)
- Mass function assignment (confidence-based)
- Evidence combination (Dempster's rule)

Intended as a working prototype to validate the pipeline before refactoring
into the modular ca/ package structure.

Usage:
    python scripts/pipeline_prototype.py

TODO:
    - Refactor extraction logic into ca/extractors/ (DONE)
    - Refactor mass functions into ca/mass_functions/
    - Refactor combiners into ca/combiners/
    - Add configuration-driven execution
"""
import json
import os

from google import genai
from dotenv import load_dotenv

from concerted_abduction.extractors.llm import LlmHypothesisExtractor

MODEL = "gemini-2.5-flash"

# System Prompt for Hypothesis Extraction
SYSTEM_PROMPT = "Hi LLM, i " \
"have given you three natural langauge inputs. We are trying to solve a problem using Dempster Shafer theory. I need you to look at these inputs from these different sources and come up with a single universe of discourse. The challenge is, each source only provides a fractional piece of the universe of discourse. Can you please do that for this example"

def load_data(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def extract_uods(sample: dict):
    extractor = LlmHypothesisExtractor(language_model=MODEL)
    extractor.set_system_prompt(SYSTEM_PROMPT)

def save_hypotheses(sample_id: str, uod: dict, output_dir: str = "results"):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{sample_id}_uod.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(uod, f, ensure_ascii=False, indent=4)
    print(f"Saved UoD for sample {sample_id} to {output_path}")

def main():
    """Main execution function for the pipeline prototype."""
    env_path = "~/.secrets/.llm_apis"
    load_dotenv(dotenv_path=os.path.expanduser(env_path))

    print("ENVIRONEMENT VARIABLES:")
    print("GEMINI_API_KEY =", os.getenv("GEMINI_API_KEY"))
    
    if not os.getenv("GEMINI_API_KEY"):
        raise EnvironmentError("GEMINI_API_KEY not found in environment variables.")
    
    data_path = "data/generated_dataset.json"
    dataset = load_data(data_path)
    print("Loaded dataset:\n", dataset)

    for sample in dataset['samples']:
        print(sample)
        breakpoint()

if __name__ == "__main__":
    main()
