from abc import ABC, abstractmethod

from concerted_abduction.types import DataSample, ExtractorOutput

class HypothesisExtractor(ABC):
    """Base class for Hypothesis Extractors."""

    @abstractmethod
    def create_uod(self, inputs: DataSample) -> ExtractorOutput:
        """Create universe of discourse from input."""
        pass
