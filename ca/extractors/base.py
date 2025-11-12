from abc import ABC, abstractmethod

class HypothesisExtractor(ABC):
    """"""

    @abstractmethod
    def extract(self, text: str):
        pass
