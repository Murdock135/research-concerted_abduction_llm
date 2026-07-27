from .base import HypothesisExtractor
from .registry import ExtractorRegistry

from google import genai
from pydantic import BaseModel, Field

# Output schema for the LlmHypothesisExtractor

class UoD(BaseModel):
    source_info: dict[str, str] = Field(..., description="Mapping of source -> response from source. For example, 'source 1: <hypothesis of source 1>, source 2: <hypotheses of source 2>, ...")
    uod: str = Field(..., description="The power set that represents the universe of discourse. Sets are enclosed in curly braces '{}'. ")

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

    def create_uod(self, inputs):
        """Create universe of discourse from input using LLM."""

        # Instantiate the language model (google)
        client = genai.Client()
        prompt = self.system_prompt + ", Here are the inputs: " + "\n".join(inputs)

        response = client.models.generate_content(
            model=self.language_model,
            contents=prompt,
        )

        return response.text
    
    @classmethod
    def set_system_prompt(cls, prompt: str):
        """Set the system prompt for the LLM."""
        cls.system_prompt = prompt