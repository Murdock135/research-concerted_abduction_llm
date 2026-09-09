from abc import ABC, abstractmethod

from concerted_abduction.types import BpaOutput, FocalSetOutput, FodOutput


class BpaAssigner(ABC):
    """Assign a mass function to each source over the shared frame."""

    @abstractmethod
    def assign_masses(
        self, fod_output: FodOutput, focal_set_output: FocalSetOutput
    ) -> BpaOutput:
        ...
