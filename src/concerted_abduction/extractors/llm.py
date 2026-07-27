from .base import HypothesisExtractor
from .registry import ExtractorRegistry

from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field

from concerted_abduction.types import DataSample, ExtractorOutput


@ExtractorRegistry.register("llm_hypothesis_extractor")
class LlmHypothesisExtractor(HypothesisExtractor):
    """
    LLM-based hypothesis extractor for generating universe of discourse.
    
    This extractor uses a language model to analyze multiple inputs and 
    generate hypotheses for abductive reasoning. The system prompt can be 
    customized to guide the LLM's output format and reasoning approach.
    
    Attributes:
        language_model: The name/identifier of the language model to use
        system_prompt: The instruction prompt sent to the LLM
    """

    system_prompt = ""

    def __init__(self, language_model):
        self.language_model = language_model

    def create_uod(self, sample: DataSample):
        """Create universe of discourse from input using LLM.
        Args:
            A list of dicts of the form:
                [
                    {'source A': '<text>'},
                    {'source B': '<text>'},
                    ...,
                ]
        Returns:
            The universe of discourse (UoD) based on the inputs provided. The shape of the UoD
            is- 
                {
                    'source_info': {
                        'source A': <'text'>,
                        'source B': <'text'>,
                    }
                    'uod': <'text'>
                }
        """
        breakpoint()

        # Instantiate the language model (google)
        client = genai.Client()
        prompt = (
            self.system_prompt 
            + ", Here are the inputs: " 
            + "\n" 
            + '\n'.join([f"{model_output.source}:{model_output.response}" for model_output in sample.outputs])
        )

        try:
            response = client.models.generate_content(
                model=self.language_model,
                contents=prompt,
            )
        except genai_errors.APIError as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e

        if response.text is None:
            raise ValueError("LLM response contained no text")

        return ExtractorOutput(
            hypotheses={model_output.source : model_output.response for model_output in sample.outputs},
            uod=response.text
        )
    
    @classmethod
    def set_system_prompt(cls, prompt: str):
        """Set the system prompt for the LLM."""
        cls.system_prompt = prompt