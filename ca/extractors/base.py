from abc import ABC, abstractmethod

class HypothesisExtractor(ABC):
    """Base class for Hypothesis Extractors."""

    @abstractmethod
    def extract(self, text: str):
        pass
