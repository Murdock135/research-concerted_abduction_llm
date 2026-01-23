from .base import HypothesisExtractor
from .registry import ExtractorRegistry

from google import genai

@ExtractorRegistry.register("llm_hypothesis_extractor")
class LlmHypothesisExtractor(HypothesisExtractor):
    """Prototype LLM-based hypothesis extractor."""

    # TODO: Load prompt from external file
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
    


