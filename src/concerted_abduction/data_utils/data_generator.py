from concerted_abduction.types import DataSet
from concerted_abduction.utils.utils import find_project_root, load_prompt
from concerted_abduction.data_utils.base import DataGenerator
from concerted_abduction.data_utils.registry import DataGeneratorRegistry

from typing import Optional
from pathlib import Path
import json

import numpy as np
from google import genai
from google.genai import types

DEFAULT_EXAMPLES_PATH = find_project_root(__file__) / "data" / "synthetic" / "examples" / "common_input" / "v0.json"
DEFAULT_SYSTEM_PROMPT_PATH = find_project_root(__file__) / "prompts" / "data_generators" / "common_input" / "v0.txt"

@DataGeneratorRegistry.register("common_input")
class CommonInputDataGenerator(DataGenerator):

    system_prompt = load_prompt(DEFAULT_SYSTEM_PROMPT_PATH)

    def __init__(self, language_model, system_prompt: Optional[str] = None, examples_path: Optional[str | Path] = None) -> None:
        self.language_model = language_model
        self._set_example_path(examples_path if examples_path is not None else DEFAULT_EXAMPLES_PATH)
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