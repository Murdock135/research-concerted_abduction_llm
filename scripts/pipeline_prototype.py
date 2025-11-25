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
    - Refactor extraction logic into ca/extractors/
    - Refactor mass functions into ca/mass_functions/
    - Refactor combiners into ca/combiners/
    - Add configuration-driven execution
"""
import json
import os

from google import genai
from dotenv import load_dotenv

from ca.extractors.base import HypothesisExtractor
from ca.extractors.registry import ExtractorRegistry

MODEL = "gemini-2.5-flash"

# System Prompt for Hypothesis Extraction
SYSTEM_PROMPT = "Hi LLM, i " \
"have given you three natural langauge inputs. We are trying to solve a problem using Dempster Shafer theory. I need you to look at these inputs from these different sources and come up with a single universe of discourse. The challenge is, each source only provides a fractional piece of the universe of discourse. Can you please do that for this example"

@ExtractorRegistry.register("llm_hypothesis_extractor")
class LlmHypothesisExtractor(HypothesisExtractor):
    """Prototype LLM-based hypothesis extractor."""

    system_prompt = SYSTEM_PROMPT

    def __init__(self, language_model):
        self.language_model = language_model

    def create_uod(self, inputs):
        """Create universe of discourse from input using LLM."""

        # Instantiate the language model (google)
        client = genai.Client()
        prompt = self.system_prompt + ", Here are the inputs: " + "\n".join(inputs)

        breakpoint()
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        return response.text


def main():
    """Main execution function for the pipeline prototype."""
    env_path = "~/.secrets/.llm_apis"
    load_dotenv(dotenv_path=os.path.expanduser(env_path))

    print("ENVIRONEMENT VARIABLES:")
    print("GEMINI_API_KEY =", os.getenv("GEMINI_API_KEY"))
    
    if not os.getenv("GEMINI_API_KEY"):
        raise EnvironmentError("GEMINI_API_KEY not found in environment variables.")
        
    # Get llm outputs
    data_path = "data/synthetic.json"
    with open(data_path, "r") as f:
        data = json.load(f)

    model_A_output = data["llm_outputs"]["model_A"]["response"]
    model_B_output = data["llm_outputs"]["model_B"]["response"]
    model_C_output = data["llm_outputs"]["model_C"]["response"]
    inputs = [model_A_output, model_B_output, model_C_output]

    # Initialize and run the hypothesis extractor
    extractor = LlmHypothesisExtractor(language_model=MODEL)

    uod = extractor.create_uod(inputs=inputs)
    print("Universe of Discourse (UoD):", uod)

if __name__ == "__main__":
    main()
