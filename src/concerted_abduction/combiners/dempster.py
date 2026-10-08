"""Combine evidence using normalized Dempster's rule.

SourceBpa objects -> mass dictionaries -> unnormalized reduction -> final normalization.
Frozenset keys let multiple focal-set pairs contribute to the same intersection.
"""

from collections import defaultdict
from math import fsum
from concerted_abduction.types import (
    BpaOutput, CombinedMass, CombinedMasses, MassFunction, SourceBpa,
)

from .base import Combiner
from .registry import CombinerRegistry


def to_mass_function(source: SourceBpa) -> MassFunction:
    """An auxiliary function that converts the pydantic model SourceBpa into a (set -> float) mapping for easier use downstream."""
    total_mass = fsum(entry.mass for entry in source.masses)
    return {
        frozenset(entry.hypotheses): entry.mass / total_mass # Correct rounding errors in source totals.
        for entry in source.masses
        if entry.mass > 0
    }


@CombinerRegistry.register("Dempster")
class DempsterCombination(Combiner):
    def combine(self, bpa_assignments: BpaOutput) -> tuple[CombinedMasses, float]:
        """Use Dempster's combination rule to combine masses"""
        mass_functions = [to_mass_function(source) for source in bpa_assignments.sources]
        cumulative_conflict = 0.0

        combined = mass_functions[0]
        for next_mass_function in mass_functions[1:]:
            combined, k = self.combine_two_sources(combined, next_mass_function)
            cumulative_conflict += k

        # This is 1 - cumulative_conflict, computed without cancellation near k=1.
        normalization_factor = fsum(combined.values())
        if normalization_factor == 0:
            raise ValueError(
                "Dempster combination is undefined under total conflict (k=1)."
            )

        result = CombinedMasses(combined_masses=[
            CombinedMass(
                focal_set=set(focal_set), combined_mass=mass / normalization_factor
            )
            for focal_set, mass in combined.items()
        ])
        return result, cumulative_conflict

    def combine_two_sources(
        self, first: MassFunction, second: MassFunction
    ) -> tuple[MassFunction, float]:
        """Return unnormalized intersection masses and newly conflicting mass."""
        mass_by_intersection: defaultdict[frozenset[str], float] = defaultdict(float)
        k = 0.0

        for first_focal_set, first_mass in first.items():
            for second_focal_set, second_mass in second.items():
                intersection = first_focal_set & second_focal_set
                mass_product = first_mass * second_mass
                if mass_product == 0:
                    continue

                if not intersection:
                    k += mass_product
                else:
                    mass_by_intersection[intersection] += mass_product

        return dict(mass_by_intersection), k
