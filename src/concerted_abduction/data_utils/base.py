from abc import ABC, abstractmethod

from concerted_abduction.types import DataSet

class DataGenerator(ABC):
    """Base class for Data Generators."""

    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    def generate_data(self, prompt: str) -> DataSet:
        """Generate a dataset."""
        pass
