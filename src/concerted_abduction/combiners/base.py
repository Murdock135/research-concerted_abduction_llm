from abc import ABC, abstractmethod

from ..types import BpaOutput


class Combiner(ABC):
    @abstractmethod
    def combine(self, bpa_assignments: BpaOutput) -> object:
        """Combine source masses into an implementation-specific result."""
        ...
