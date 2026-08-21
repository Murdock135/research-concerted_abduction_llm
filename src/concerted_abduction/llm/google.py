from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import BaseModel

from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.llm.registry import LanguageModelRegistry

@LanguageModelRegistry.register('gemini-google_genai')
class GeminiLanguageModel(LanguageModel):
    def generate(
        self,
        prompt: str,
        temp: int = 0,
        top_p: int = 1,
        output_schema: type[BaseModel] | None = None,
    ) -> BaseModel | str:
        # Instantiate the language model (google)
        client = genai.Client()

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=self.system_prompt or None,
                    response_mime_type=(
                        "application/json" if output_schema is not None else None
                    ),
                    response_schema=output_schema,
                ),
            )
        except genai_errors.APIError as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e

        if response.text is None:
            raise ValueError("Gemini did not return any text")

        if output_schema is not None:
            return output_schema.model_validate_json(response.text)

        return response.text
