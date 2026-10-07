"""Define the shared contract and input/output helpers for evidence combiners.

1. Define what every combiner implements.
   EvidenceCombiner is an ABC (abstract base class). Its @abstractmethod markers
   require subclasses to implement from_config() and combine(). from_config()
   constructs an instance from settings; combine() applies that method's rule.
   A typical subclass calls the shared helpers in this order:
       BpaOutput + FrameOfDiscernment
                    |
             _prepare_inputs()
                    |
             PreparedEvidence
                    |
          subclass's combination rule
                    |
              _build_result()
                    |
             CombinedEvidence

2. Prepare the inputs with _prepare_inputs().
   BpaOutput contains source BPAs (basic probability assignments); the shared
   FrameOfDiscernment lists allowed hypothesis labels. Pydantic's model_dump()
   converts objects to ordinary data; model_validate() rechecks and copies it,
   catching invalid objects even if they were modified after construction.

   Each source's mass entries become a subset-to-mass dictionary:
       hypotheses=["a", "b"], mass=0.4 -> {frozenset({"a", "b"}): 0.4}
   This is a MassDistribution. frozenset is an immutable set usable as a dictionary
   key, so label order does not matter. issubset() checks frame membership; fsum()
   computes source totals with less rounding error than ordinary addition.
   PreparedEvidence groups the copied frame, source names, dictionaries, and totals
   in corresponding order: sources[i] identifies source_masses[i].

3. Let the subclass combine the prepared evidence.
   The subclass decides whether to normalize inputs, how to handle conflict, and
   whether to process sources sequentially or jointly. The base helpers preserve
   supplied masses; they impose neither normalization nor a combination strategy.

4. Format and validate the output with _build_result().
   The subclass supplies its final mass dictionary, method name, and diagnostics.
   This helper orders subsets consistently and writes their labels in frame order:
       frozenset({"b", "a"}): 0.4 -> CombinedMass(hypotheses=["a", "b"], mass=0.4)
   Empty-set mass becomes hypotheses=[] for methods that retain conflict.
   CombinedEvidence groups these entries with the frame, source names, method,
   optional conflict total, and diagnostics. JsonValue allows JSON-compatible
   diagnostic values such as numbers, strings, lists, and dictionaries. Pydantic
   validates the completed output; this helper does not normalize or clip masses.
"""

from abc import ABC, abstractmethod
from math import fsum

from pydantic import JsonValue

from concerted_abduction.types import (
    BpaOutput,
    CombinedEvidence,
    CombinedMass,
    FrameOfDiscernment,
)
from config.settings import CombinerConfig

from .types import MassDistribution, PreparedEvidence


class EvidenceCombiner(ABC):
    """Contract and shared helpers for evidence-combination methods."""

    @classmethod
    @abstractmethod
    def from_config(cls, cfg: CombinerConfig) -> "EvidenceCombiner":
        """Construct a subclass instance from configuration."""
        ...

    @abstractmethod
    def combine(
        self, bpa_output: BpaOutput, frame: FrameOfDiscernment
    ) -> CombinedEvidence:
        """Merge source BPAs over the shared frame using the subclass's rule."""
        ...

    def _prepare_inputs(
        self, bpa_output: BpaOutput, frame: FrameOfDiscernment
    ) -> PreparedEvidence:
        """Validate and copy inputs into subset-to-mass mappings without normalization."""
        # Running example: frame=["a", "b"], sources "A" and "B".
        # A supports {a}: 0.6, {a,b}: 0.4; B supports {b}: 0.7, {a,b}: 0.3.
        # Revalidate nested instances because callers can mutate them after creation.
        bpa = BpaOutput.model_validate(bpa_output.model_dump())  # BpaOutput(sources=[SourceBpa(...), ...])
        frame = FrameOfDiscernment.model_validate(frame.model_dump())  # FrameOfDiscernment(frame=["a", "b"])
        labels = frame.frame  # ["a", "b"]: allowed hypothesis labels.
        universe = frozenset(labels)  # frozenset({"a", "b"}): the full frame as a set.
        sources = []  # Grows to ["A", "B"], preserving input order.
        source_masses = []  # Grows to [A's mass dictionary, B's mass dictionary].
        input_mass_totals = []  # Grows to [1.0, 1.0], one total per source.
        for source in bpa.sources:
            # source is a SourceBpa: source.source="A", source.masses=[FocalSetMass(...), ...].
            distribution: MassDistribution = {}  # For A: {frozenset({"a"}): 0.6, frozenset({"a", "b"}): 0.4}.
            for entry in source.masses:
                # entry is a FocalSetMass: hypotheses=["a"], mass=0.6, justification="...".
                subset = frozenset(entry.hypotheses)  # ["a"] -> frozenset({"a"}); each hypothesis is a string.
                if not subset.issubset(universe):
                    raise ValueError(
                        f"Source {source.source!r} contains hypotheses outside the frame"
                    )
                distribution[subset] = entry.mass  # Adds frozenset({"a"}): 0.6 on the first iteration.
            sources.append(source.source)
            source_masses.append(distribution)
            input_mass_totals.append(fsum(distribution.values()))

        # PreparedEvidence keeps parallel lists: sources[i] identifies source_masses[i].
        return PreparedEvidence(
            frame=frame,
            sources=sources,
            source_masses=source_masses,
            input_mass_totals=input_mass_totals,
        )

    def _build_result(
        self,
        *,
        frame: FrameOfDiscernment,
        sources: list[str],
        masses: MassDistribution,
        combiner: str,
        diagnostics: dict[str, JsonValue],
        conflict_mass: float | None = None,
    ) -> CombinedEvidence:
        """Order subset masses consistently and construct validated CombinedEvidence."""
        # Example masses (rounded): {frozenset({"a"}): 0.3103,
        #     frozenset({"b"}): 0.4828, frozenset({"a", "b"}): 0.2069}.
        # sources=["A", "B"], combiner="dempster", conflict_mass=0.42.
        # diagnostics is a dictionary, e.g. {"steps": [{"source": "B", ...}], ...}.
        ordered_subsets = sorted(masses, key=lambda subset: (len(subset), tuple(sorted(subset))))
        # ordered_subsets = [frozenset({"a"}), frozenset({"b"}), frozenset({"a", "b"})].
        entries = []  # Grows to [CombinedMass(hypotheses=["a"], mass=...), ...].
        for subset in ordered_subsets:
            # subset is one key, e.g. frozenset({"a", "b"}); masses[subset] is its float mass.
            # Do not silently discard unknown labels while imposing frame order.
            if not subset.issubset(frame.frame):
                raise ValueError("Combined mass subset contains hypotheses outside the frame")
            entries.append(CombinedMass(
                # label is "a" or "b"; this produces ["a", "b"] in frame order.
                hypotheses=[label for label in frame.frame if label in subset],
                mass=masses[subset],
            ))
        return CombinedEvidence(
            frame=frame,
            sources=sources,
            combiner=combiner,
            masses=entries,
            conflict_mass=conflict_mass,
            diagnostics=diagnostics,
        )
