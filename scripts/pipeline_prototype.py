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

from typing import List
import json
import os

from pydantic import BaseModel, Field
from google import genai
from dotenv import load_dotenv



MODEL = "gemini-2.5-flash"

# System Prompt for Hypothesis Extraction
SYSTEM_PROMPT = """You are a helpful assistant that takes in language model outputs and treat them as evidence that the language model is trying to solve and finally generates a hypothesis with a confidence score in the range [0-1].
Your output should have the following 3 items:

1. statement: Your best guess of the hypothesis statement implied by the language model output.
2. confidence: A float number between 0 and 1 representing your confidence in the hypothesis.
3. rationale: A brief explanation of why you assigned that confidence score.

Here is the language model output you need to analyze:
"""


class Hypothesis(BaseModel):
    """Represents a hypothesis with associated confidence."""
    statement: str = Field(..., description="The hypothesis statement.")
    confidence: float = Field(..., description="Confidence score between 0 and 1.")
    rationale: str = Field(..., description="Rationale for the confidence score.")


class LlmHypothesisExtractor:
    """Prototype LLM-based hypothesis extractor."""

    system_prompt = SYSTEM_PROMPT

    def __init__(self, language_model, inputs: List[str]):
        self.inputs = inputs
        self.language_model = language_model

    def extract_hypothesis(self, input):
        # Instantiate the language model (google)
        client = genai.Client()
        prompt = self.system_prompt + input

        breakpoint()
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": Hypothesis.model_json_schema(),
            },
        )

        breakpoint()
        return Hypothesis.model_validate_json(response.text)

    def run(self):
        self.hypotheses: List[Hypothesis] = []
        for input_text in self.inputs:
            hypothesis = self.extract_hypothesis(input=input_text)
            self.hypotheses.append(hypothesis)

    def get_hypotheses(self) -> List[Hypothesis]:
        return self.hypotheses


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
    extractor = LlmHypothesisExtractor(language_model=MODEL, inputs=inputs)
    extractor.run()

    # Retrieve and print hypotheses
    hypotheses = extractor.get_hypotheses()

    # Print the extracted hypotheses
    for idx, hypothesis in enumerate(hypotheses):
        print(f"Hypothesis {idx + 1}:")
        print(f"Statement: {hypothesis.statement}")
        print(f"Confidence: {hypothesis.confidence}")
        print(f"Rationale: {hypothesis.rationale}")
        print("-" * 40)

if __name__ == "__main__":
    main()
