import itertools
import json
import tempfile
import unittest
from math import prod
from pathlib import Path

from pydantic import ValidationError

from concerted_abduction.combiners import (
    CombinerRegistry, DempsterCombiner, EvidenceCombiner, TotalConflictError,
)
from concerted_abduction.types import (
    BpaOutput, CombinedEvidence, FocalSetMass, FrameOfDiscernment, SourceBpa,
)
from config.settings import CombinerConfig, ConcertedAbductionSettings
from scripts.run import create_combiner, save_combined


def bpas(*distributions):
    return BpaOutput(sources=[SourceBpa(source=f"source-{i}", masses=[
        FocalSetMass(hypotheses=list(subset), mass=mass, justification="Fixture")
        for subset, mass in distribution
    ]) for i, distribution in enumerate(distributions)])


def mass_map(result):
    return {frozenset(entry.hypotheses): entry.mass for entry in result.masses}


class CombinerTests(unittest.TestCase):
    def setUp(self):
        self.frame = FrameOfDiscernment(frame=["a", "b", "c"])
        self.combiner = DempsterCombiner()

    def test_agreement(self):
        result = self.combiner.combine(bpas([(["a"], 1)], [(["a"], 1)]), self.frame)
        self.assertEqual(mass_map(result), {frozenset(["a"]): 1})
        self.assertEqual(result.conflict_mass, 0)

    def test_partial_overlap_and_conflict(self):
        result = self.combiner.combine(bpas(
            [(["a", "b"], .6), (["c"], .4)],
            [(["a"], .5), (["b", "c"], .5)],
        ), self.frame)
        masses = mass_map(result)
        for hypothesis, expected in [("a", .375), ("b", .375), ("c", .25)]:
            self.assertAlmostEqual(masses[frozenset([hypothesis])], expected)
        assert result.conflict_mass is not None
        self.assertAlmostEqual(result.conflict_mass, .2)

    def test_composite_mass_is_preserved(self):
        result = self.combiner.combine(bpas(
            [(["a", "b"], .7), (["a", "b", "c"], .3)],
            [(["a", "b", "c"], 1)],
        ), self.frame)
        self.assertAlmostEqual(mass_map(result)[frozenset(["a", "b"])], .7)
        self.assertEqual(len(result.masses), 2)

    def test_tiny_conflict_is_not_lost_to_subtraction(self):
        result = self.combiner.combine(bpas(
            [(["a"], 1)], [(["a"], 1-1e-18), (["b"], 1e-18)],
        ), self.frame)
        self.assertEqual(result.conflict_mass, 1e-18)

    def test_single_source_and_vacuous_identity(self):
        original = bpas([(["b", "a"], .4), (["c"], .6)])
        before = original.model_dump()
        result = self.combiner.combine(original, self.frame)
        self.assertEqual(result.sources, ["source-0"])
        self.assertEqual(result.diagnostics["steps"], [])
        self.assertEqual(original.model_dump(), before)
        self.assertEqual(result.masses[0].hypotheses, ["c"])

    def test_multiple_sources_against_direct_cartesian_combination(self):
        distributions = [
            [(["a"], .6), (["a", "b", "c"], .4)],
            [(["b"], .7), (["a", "b", "c"], .3)],
            [(["a", "b"], .8), (["c"], .2)],
        ]
        raw = {}
        for entries in itertools.product(*distributions):
            intersection = frozenset.intersection(*(frozenset(s) for s, _ in entries))
            raw[intersection] = raw.get(intersection, 0) + prod(m for _, m in entries)
        conflict = raw.pop(frozenset(), 0)
        for permutation in itertools.permutations(distributions):
            result = self.combiner.combine(bpas(*permutation), self.frame)
            self.assertAlmostEqual(result.conflict_mass, conflict)
            for subset, mass in raw.items():
                self.assertAlmostEqual(mass_map(result)[subset], mass / (1-conflict))
            steps = result.diagnostics["steps"]
            assert isinstance(steps, list)
            self.assertEqual(len(steps), 2)

    def test_total_and_near_total_conflict(self):
        with self.assertRaises(TotalConflictError):
            self.combiner.combine(bpas([(["a"], 1)], [(["b"], 1)]), self.frame)
        data = bpas([(["a"], 1)], [(["a"], 1e-13), (["b"], 1-1e-13)])
        with self.assertRaises(TotalConflictError):
            self.combiner.combine(data, self.frame)
        result = DempsterCombiner(1e-15).combine(data, self.frame)
        self.assertEqual(mass_map(result), {frozenset(["a"]): 1})

    def test_input_validation_including_mutated_instances(self):
        for mutation in [
            lambda b: setattr(b.sources[0].masses[0], "mass", float("nan")),
            lambda b: setattr(b.sources[0].masses[0], "mass", .5),
            lambda b: setattr(b.sources[0].masses[0], "hypotheses", []),
            lambda b: setattr(b.sources[0].masses[0], "hypotheses", ["outside"]),
            lambda b: setattr(b.sources[0].masses[0], "hypotheses", ["a", "a"]),
            lambda b: b.sources.append(b.sources[0]),
            lambda b: b.sources[0].masses.append(b.sources[0].masses[0]),
            lambda b: setattr(b, "sources", []),
        ]:
            data = bpas([(["a"], 1)])
            mutation(data)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.combiner.combine(data, self.frame)
        for labels in [[], ["a", "a"], [" "]]:
            with self.subTest(labels=labels), self.assertRaises(ValueError):
                self.combiner.combine(bpas([(["a"], 1)]), FrameOfDiscernment(frame=labels))

    def test_accepted_input_rounding_is_recorded_and_corrected(self):
        data = bpas([(["a"], .5000001), (["b"], .5)])
        result = self.combiner.combine(data, self.frame)
        self.assertAlmostEqual(sum(m.mass for m in result.masses), 1)
        totals = result.diagnostics["input_mass_totals"]
        assert isinstance(totals, list) and isinstance(totals[0], float)
        self.assertAlmostEqual(totals[0], 1.0000001)

    def test_shared_input_preparation_preserves_masses_and_copies_inputs(self):
        data = bpas([(["a"], .5000001), (["b"], .5), (["c"], 0)])
        prepared = self.combiner._prepare_inputs(data, self.frame)
        self.assertEqual(prepared.source_masses[0][frozenset(["a"])], .5000001)
        self.assertEqual(prepared.source_masses[0][frozenset(["c"])], 0)
        self.assertAlmostEqual(prepared.input_mass_totals[0], 1.0000001)
        prepared.source_masses[0][frozenset(["a"])] = .1
        prepared.frame.frame.append("new")
        self.assertEqual(data.sources[0].masses[0].mass, .5000001)
        self.assertNotIn("new", self.frame.frame)

    def test_shared_result_builder_preserves_conflict_and_rejects_unknown_labels(self):
        result = self.combiner._build_result(
            frame=self.frame,
            sources=["source"],
            masses={frozenset(["a", "b"]): .8, frozenset(): .2},
            combiner="test_conjunctive",
            diagnostics={},
            conflict_mass=.2,
        )
        self.assertEqual(result.masses[0].hypotheses, [])
        self.assertEqual(result.masses[0].mass, .2)
        self.assertEqual(result.masses[1].hypotheses, ["a", "b"])
        with self.assertRaisesRegex(ValueError, "outside the frame"):
            self.combiner._build_result(
                frame=self.frame,
                sources=["source"],
                masses={frozenset(["a", "outside"]): 1},
                combiner="test",
                diagnostics={},
            )

    def test_registry_and_configuration(self):
        settings = ConcertedAbductionSettings()  # pyright: ignore[reportCallIssue]
        self.assertIs(CombinerRegistry._get(settings.combiner.type), DempsterCombiner)
        self.assertIsInstance(create_combiner(settings.combiner), EvidenceCombiner)
        self.assertEqual(settings.combiner.output_dir, settings.bpa.output_dir)
        with self.assertRaisesRegex(ValueError, "Unknown combiner"):
            CombinerRegistry._get("missing")
        with self.assertRaisesRegex(ValueError, "already registered"):
            CombinerRegistry.register("dempster")(DempsterCombiner)
        with self.assertRaises(TypeError):
            CombinerRegistry.register("invalid")(object)  # pyright: ignore[reportArgumentType]
        for value in [0, -1, 1, float("nan"), float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                DempsterCombiner(value)
            with self.assertRaises(ValidationError):
                CombinerConfig(type="dempster", output_dir=Path("experiments/runs"), numerical_tolerance=value)

    def test_second_registered_method(self):
        class IdentityCombiner(EvidenceCombiner):
            @classmethod
            def from_config(cls, cfg):
                return cls()

            def combine(self, bpa_output, frame):
                inputs = self._prepare_inputs(bpa_output, frame)
                if len(inputs.sources) != 1:
                    raise ValueError("Identity fixture accepts exactly one source")
                return self._build_result(
                    frame=inputs.frame,
                    sources=inputs.sources,
                    masses=inputs.source_masses[0],
                    combiner="test_identity",
                    diagnostics={},
                )

        try:
            CombinerRegistry.register("test_identity")(IdentityCombiner)
            combiner = create_combiner(CombinerConfig(type="test_identity", output_dir=Path("experiments/runs")))
            self.assertIsInstance(combiner, IdentityCombiner)
            self.assertEqual(combiner.combine(bpas([(["a"], 1)]), self.frame).combiner, "test_identity")
        finally:
            CombinerRegistry._combiners.pop("test_identity", None)

    def test_artifact_round_trip_and_method_neutral_empty_set(self):
        result = self.combiner.combine(bpas([(["a"], 1)]), self.frame)
        with tempfile.TemporaryDirectory() as directory:
            save_combined(Path(directory), "scenario", result)
            payload = json.loads((Path(directory) / "scenario_combined.json").read_text())
            self.assertEqual(CombinedEvidence.model_validate(payload), result)
        payload = result.model_dump()
        payload["masses"] = [{"hypotheses": [], "mass": .2}, {"hypotheses": ["a"], "mass": .8}]
        self.assertEqual(CombinedEvidence.model_validate(payload).masses[0].hypotheses, [])

    def test_combined_output_rejects_invalid_distributions(self):
        result = self.combiner.combine(bpas([(["a"], 1)]), self.frame)
        for masses in [
            [{"hypotheses": ["outside"], "mass": 1}],
            [{"hypotheses": ["a", "a"], "mass": 1}],
            [{"hypotheses": ["a"], "mass": .5}],
            [{"hypotheses": ["a"], "mass": .5}, {"hypotheses": ["a"], "mass": .5}],
        ]:
            payload = result.model_dump()
            payload["masses"] = masses
            with self.subTest(masses=masses), self.assertRaises(ValidationError):
                CombinedEvidence.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
