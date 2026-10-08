from abc import ABC, abstractmethod

from ..types import BpaOutput, CombinedMasses


class Combiner(ABC):
    @abstractmethod
    def combine(self, bpa_assignments: BpaOutput) -> tuple[CombinedMasses, float]:
        """Combine masses"""
        ...
