from abc import ABC, abstractmethod

from concerted_abduction.types import FocalSetOutput, FodOutput


class FocalSetCreator(ABC):
    """Base class for components that derive focal sets from FoD output."""

    @abstractmethod
    def create_focal_sets(self, fod_output: FodOutput) -> FocalSetOutput:
        """Create supported focal sets for every source in ``fod_output``."""
        ...
