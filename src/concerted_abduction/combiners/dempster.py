"""Combine source evidence using Dempster's rule and report conflicting mass.

Configuration name "dempster" selects DempsterCombiner through its registry
decorator. from_config() constructs the instance; Self denotes its return type.
combine() then follows the progression below, using one running example.

1. Prepare the source masses.
   BpaOutput holds source BPAs (basic probability assignments); the shared
   FrameOfDiscernment lists allowed hypothesis labels. For frame {a, b}:
       source A: {a}: 0.6, {a,b}: 0.4
       source B: {b}: 0.7, {a,b}: 0.3
   EvidenceCombiner._prepare_inputs() validates these and returns PreparedEvidence.
   Its dictionaries use frozenset keys: {frozenset({"a"}): 0.6, ...}.
   combine() divides each source's masses by its total to correct accepted rounding
   differences. Here each total is 1, so the values remain unchanged.

2. Combine two distributions in _combine_pair().
   A "step" multiplies every pair of masses (*) and intersects their subsets (&):
       A subset   B subset   intersection   mass product
       {a}        {b}        empty          0.6 * 0.7 = 0.42
       {a}        {a,b}      {a}            0.6 * 0.3 = 0.18
       {a,b}      {b}        {b}            0.4 * 0.7 = 0.28
       {a,b}      {a,b}      {a,b}          0.4 * 0.3 = 0.12

   defaultdict(list) collects products with the same intersection; fsum() sums
   each list accurately. pop(frozenset(), []) removes the empty-set group,
   whose total is conflict K. Only those contributions are discarded, not sources
   or labels. "Survival" is the remaining mass before normalization:
       1.00 total = 0.42 conflict + 0.58 surviving mass
       normalized masses: {a}: 0.18/0.58, {b}: 0.28/0.58, {a,b}: 0.12/0.58
   Dividing by survival (mathematically 1-K) makes the result sum to one; composite
   subsets keep their mass intact. Summing survivors directly avoids cancellation
   near K=1. TotalConflictError rejects survival at/below numerical_tolerance.

3. Include every remaining source in the running result.
       A --+
           +-- step 1 --> AB --+
       B --+                  +-- step 2 --> ABC
       C ---------------------+
   N sources need N-1 steps; one source needs none. AB already contains both A's
   and B's contributions. Adding C accounts for all triples of focal sets:
       intersection X & Y & Z; raw mass product m_A(X) * m_B(Y) * m_C(Z)
   Dempster's rule is associative: grouping does not change final masses in exact
   arithmetic when normalization is defined. Sequential processing therefore
   matches joint combination, while merging equal intersections along the way.
   Combining AB, AC, and BC again would count each source twice. Floating-point
   rounding and the numerical threshold can make processing order matter in code.

4. Preserve conflict information and construct the output.
   Each step normalizes its result, so its conflict is conditional on prior
   survival. cumulative_survival multiplies survival factors; cumulative_conflict
   weights new conflict by that surviving fraction. For step conflicts 0.20, 0.30:
       overall conflict = 0.20 + 0.80 * 0.30 = 0.44
   _build_result() formats the final masses as CombinedEvidence. conflict_mass
   stores overall conflict; diagnostics["steps"] stores each incoming source,
   conflict, and survival. These are totals, not individual conflicting pairs.
   scripts/run.py saves the output in the scenario's _combined.json artifact.
"""

from collections import defaultdict
from math import fsum, isfinite
from typing import Self

from pydantic import JsonValue

from concerted_abduction.types import BpaOutput, CombinedEvidence, FrameOfDiscernment
from config.settings import CombinerConfig

from .base import EvidenceCombiner
from .registry import CombinerRegistry
from .types import MassDistribution


class TotalConflictError(ValueError):
    """Raised when surviving mass is zero or at/below the numerical threshold."""


@CombinerRegistry.register("dempster")
class DempsterCombiner(EvidenceCombiner):
    """Apply Dempster's rule sequentially and record discarded conflict."""

    def __init__(self, numerical_tolerance: float = 1e-12):
        """Set a finite cutoff below which normalization is rejected, including equality."""
        if not isfinite(numerical_tolerance) or not 0 < numerical_tolerance < 1:
            raise ValueError("numerical_tolerance must be finite and between zero and one")
        self.numerical_tolerance = numerical_tolerance  # Default 1e-12 = 0.000000000001.

    @classmethod
    def from_config(cls, cfg: CombinerConfig) -> Self:
        """Build a combiner with the configured numerical tolerance."""
        # cfg is a CombinerConfig, e.g. type="dempster", numerical_tolerance=1e-12.
        return cls(numerical_tolerance=cfg.numerical_tolerance)

    def combine(self, bpa_output: BpaOutput, frame: FrameOfDiscernment) -> CombinedEvidence:
        """Combine sources sequentially and return masses with conflict diagnostics."""
        # Running example: frame=["a", "b"], sources=["A", "B"].
        # A: {a}: 0.6, {a,b}: 0.4. B: {b}: 0.7, {a,b}: 0.3.
        # Set shorthand {a,b} below means frozenset({"a", "b"}); results are rounded.
        inputs = self._prepare_inputs(bpa_output, frame)
        # inputs is PreparedEvidence: sources=["A", "B"], input_mass_totals=[1.0, 1.0],
        # source_masses=[{frozenset({"a"}): 0.6, frozenset({"a", "b"}): 0.4}, B's mapping].

        # Dempster's rule corrects rounding accepted by SourceBpa's 1e-6 tolerance.
        # The shared base class deliberately leaves normalization to each method.
        distributions = []  # Grows to one normalized mass dictionary per source.
        for source_masses, total in zip(inputs.source_masses, inputs.input_mass_totals):
            # source_masses is A's mapping on the first pass; total is 1.0.
            distributions.append({
                # subset=frozenset({"a"}), mass=0.6 -> the same key with mass 0.6 / 1.0.
                subset: mass / total
                for subset, mass in source_masses.items()
                if mass > 0
            })

        combined_masses = distributions[0]  # Starts as A's mapping: {{a}: 0.6, {a,b}: 0.4}.
        steps: list[JsonValue] = []  # Grows to [{"source": "B", "conflict_mass": 0.42, ...}].
        cumulative_survival = 1.0  # Fraction surviving all steps so far; 1.0 -> 0.58.
        cumulative_conflict = 0.0  # Overall discarded mass so far; 0.0 -> 0.42.
        for source, next_source_masses in zip(inputs.sources[1:], distributions[1:]):
            # source="B"; next_source_masses={{b}: 0.7, {a,b}: 0.3}.
            combined_masses, conflict_mass, non_conflicting_mass = self._combine_pair(
                combined_masses, next_source_masses, source=source
            )
            # Returns {{a}: 0.3103, {b}: 0.4828, {a,b}: 0.2069}, 0.42, 0.58.
            # Step conflict is conditional on previous survival. Weight it to
            # recover overall discarded mass without subtraction from one.
            cumulative_conflict = fsum((
                cumulative_conflict, cumulative_survival * conflict_mass
            ))
            cumulative_survival *= non_conflicting_mass
            steps.append({
                "source": source,
                "conflict_mass": conflict_mass,
                "non_conflicting_mass": non_conflicting_mass,
            })

        return self._build_result(
            frame=inputs.frame,
            sources=inputs.sources,
            masses=combined_masses,
            combiner="dempster",
            conflict_mass=min(1.0, max(0.0, cumulative_conflict)),
            diagnostics={
                "steps": steps,
                "input_mass_totals": list[JsonValue](inputs.input_mass_totals),
                "numerical_tolerance": self.numerical_tolerance,
                "cumulative_non_conflicting_mass": cumulative_survival,
            },
        )

    def _combine_pair(
        self,
        first: MassDistribution,
        second: MassDistribution,
        *,
        source: str,
    ) -> tuple[MassDistribution, float, float]:
        """Return (normalized intersection masses, conflict K, surviving mass)."""
        # first={{a}: 0.6, {a,b}: 0.4}; second={{b}: 0.7, {a,b}: 0.3}; source="B".
        # Keys are frozensets, e.g. {a} means frozenset({"a"}).
        intersection_contributions: dict[frozenset[str], list[float]] = defaultdict(list)
        # Starts empty; each key will collect a list of products, e.g. {frozenset(): [0.42]}.
        for first_subset, first_mass in first.items():
            # First pass: first_subset=frozenset({"a"}), first_mass=0.6.
            for second_subset, second_mass in second.items():
                # First pass: second_subset=frozenset({"b"}), second_mass=0.7.
                intersection = first_subset & second_subset  # {a} & {b} -> frozenset() (empty).
                intersection_contributions[intersection].append(first_mass * second_mass)
                # Adds 0.6 * 0.7 = 0.42 to the empty-set contribution list.

        # After all pairs: {empty: [0.42], {a}: [0.18], {b}: [0.28], {a,b}: [0.12]}.
        conflict_mass = fsum(intersection_contributions.pop(frozenset(), []))  # K = 0.42.
        intersection_masses = {
            # subset=frozenset({"a"}), contributions=[0.18] -> mass 0.18.
            subset: fsum(contributions)
            for subset, contributions in intersection_contributions.items()
        }
        # intersection_masses={{a}: 0.18, {b}: 0.28, {a,b}: 0.12}; empty key removed.
        # Sum survivors rather than subtract K from one to avoid cancellation.
        non_conflicting_mass = fsum(intersection_masses.values())  # 0.18 + 0.28 + 0.12 = 0.58.
        if non_conflicting_mass <= self.numerical_tolerance:
            raise TotalConflictError(
                f"Cannot combine source {source!r}: non-conflicting mass "
                f"{non_conflicting_mass:.17g} <= numerical_tolerance {self.numerical_tolerance:g}"
            )

        combined_masses = {
            # For {a}: 0.18 / 0.58 = about 0.3103.
            subset: mass / non_conflicting_mass
            for subset, mass in intersection_masses.items()
            if mass > 0
        }
        # combined_masses={{a}: 0.3103, {b}: 0.4828, {a,b}: 0.2069}; sums to 1.
        return combined_masses, conflict_mass, non_conflicting_mass
