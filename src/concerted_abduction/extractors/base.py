from abc import ABC, abstractmethod

from concerted_abduction.types import DataSample, ExtractorOutput

class HypothesisExtractor(ABC):
    """Base class for Hypothesis Extractors."""

    @abstractmethod
    def generate_frame(self, sample: DataSample) -> ExtractorOutput:
        """Generate a frame of discernment aka a universe of discourse from input."""
        pass
