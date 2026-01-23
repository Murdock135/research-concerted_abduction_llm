from concerted_abduction.types import DataSet
from concerted_abduction.utils.utils import find_project_root

from typing import Optional
from pathlib import Path
import json

import numpy as np
from google import genai
from google.genai import types

"""
TODO:
1. Load system_prompt from a file dynamically.
2. Get examples
"""
EXAMPLES_PATH = find_project_root(__file__) / "data" / "synthetic.json"
class DataGenerator:

    system_prompt = """You are a helpful assistant that generates natural language data samples for training machine learning models.

    The intended dataset is meant to be used in a Belief-Theory setting (Dempster-Shafer theory). Thus, 
    each sample should be a synthetic representation of an interaction between a human and multiple
    language models.

    Nature of each sample:
    The human provides an input message that implies a mystery or an uncertain situation that the language models need to reason about. 
    For example, it could be a medical diagnosis or differential diagnosis scenario (Example provided at the end). Then, 
    each language model provides a response to the input message, which may include different hypotheses or interpretations of the situation.
    Each language model's response should have some overlap in their hypotheses but may also contain unique elements or interpretations to reflect different reasoning paths.

    You will be provided a scenario description for each sample and an overlap matrix that specifies the degree of overlap of evidence between the outputs of different models for that scenario.
    
    Each sample should be a dictionary with the following keys:
    - id (str): A unique identifier
    - created_at (str): The creation timestamp of the sample. Format: YYYY-MM-DDTHH:MM:SSZ
    - input_message (str): The input text for the model to process
    - outputs (list[dict]): A list of model responses, each containing:
        - model_name (str): The name of the language model
        - response (str): The model's response to the input_message

    You will be provided an overlap matrix representing the similarity or overlap between the outputs of different models for the same input message. 
    The overlap matrix is a square matrix of size `n_models x n_models`, where each entry `(i, j)` indicates the degree of overlap between the outputs of model `i` and model `j`.

    Example:
    """

    def __init__(self, language_model, system_prompt: Optional[str] = None) -> None:
        self.language_model = language_model
        self._set_example_path(EXAMPLES_PATH)
        self.examples = self._get_examples()
        self.system_prompt = system_prompt if system_prompt is not None else self.__class__.system_prompt

        # Append the examples to the system prompt
        self.system_prompt = self.system_prompt + "\n" + json.dumps(self.examples)

    def generate_data(self, prompt: str) -> DataSet:
        """
        Example prompt:
        "Generate 5 data samples in a medical diagnosis scenario for 3 models with the following overlap matrix: [[1.0, 0.5, 0.2], [0.5, 1.0, 0.3], [0.2, 0.3, 1.0]]"
        """
        client = genai.Client()
        response = client.models.generate_content(
            model=self.language_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                response_mime_type="application/json",
                response_json_schema=DataSet.model_json_schema(),
            )
        )

        samples = DataSet.model_validate_json(response.text)
        return samples

    @classmethod
    def _set_example_path(cls, path: str | Path) -> None:
        cls.example_path = Path(path)

    @classmethod
    def _get_examples(cls, path: str | Path | None = None) -> list[dict]:
        path = cls.example_path if path is None else Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Examples file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            examples = json.load(f)
        return examples