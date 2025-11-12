from .base import HypothesisExtractor
from .registry import ExtractorRegistry

@ExtractorRegistry('llm')
class LlmExtractor(HypothesisExtractor):
    model = None

    def __init__(self, llm_model, evidence: dict):
        pass
