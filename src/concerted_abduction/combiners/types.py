"""Internal representations shared by evidence-combination methods."""

from dataclasses import dataclass

from concerted_abduction.types import FrameOfDiscernment

type MassDistribution = dict[frozenset[str], float]


@dataclass
class PreparedEvidence:
    """Validated source masses in input order, without normalization."""

    frame: FrameOfDiscernment
    sources: list[str]
    source_masses: list[MassDistribution]
    input_mass_totals: list[float]
