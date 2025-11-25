from abc import ABC, abstractmethod

class HypothesisExtractor(ABC):
    """Base class for Hypothesis Extractors."""

    @abstractmethod
    def create_uod(self, inputs):
        """Create universe of discourse from input."""
        pass
