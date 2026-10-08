import unittest
from itertools import permutations, product
from math import fsum

from pydantic import ValidationError

from concerted_abduction.combiners.dempster import (
    DempsterCombination, to_mass_function,
)
from concerted_abduction.combiners.registry import CombinerRegistry
from concerted_abduction.types import (
    BpaOutput, CombinedMass, FocalSetMass, MassFunction, SourceBpa,
)


def source(name: str, masses: MassFunction) -> SourceBpa:
    return SourceBpa(source=name, masses=[
        FocalSetMass(hypotheses=sorted(subset), mass=mass, justification="Test")
        for subset, mass in masses.items()
    ])


class CombinerTests(unittest.TestCase):
    def setUp(self):
        self.x = frozenset({"x"})
        self.y = frozenset({"y"})
        self.frame = self.x | self.y
        self.combiner = DempsterCombination()

    def test_pair_merges_intersections_without_normalizing(self):
        first = {self.x: 0.6, self.frame: 0.4}
        second = {self.y: 0.3, self.frame: 0.7}
        before = first.copy(), second.copy()
        combined, k = self.combiner.combine_two_sources(first, second)

        self.assertAlmostEqual(k, 0.18)
        for subset, expected in {self.x: 0.42, self.y: 0.12, self.frame: 0.28}.items():
            self.assertAlmostEqual(combined[subset], expected)
        self.assertAlmostEqual(fsum(combined.values()), 0.82)
        self.assertEqual((first, second), before)

        combined, k = self.combiner.combine_two_sources(first, first)
        self.assertEqual(len(combined), 2)
        self.assertAlmostEqual(combined[self.x], 0.84)
        self.assertAlmostEqual(combined[self.frame], 0.16)
        self.assertEqual(k, 0)

    def test_unnormalized_step_conflicts_can_be_added(self):
        first = {self.x: 0.8, self.y: 0.2}
        second = {self.x: 1.0}
        third = {self.x: 0.7, self.y: 0.3}

        combined, first_conflict = self.combiner.combine_two_sources(first, second)
        self.assertAlmostEqual(combined[self.x], 0.8)
        self.assertAlmostEqual(first_conflict, 0.2)
        combined, second_conflict = self.combiner.combine_two_sources(combined, third)
        self.assertAlmostEqual(combined[self.x], 0.56)
        self.assertAlmostEqual(second_conflict, 0.24)
        self.assertAlmostEqual(first_conflict + second_conflict, 0.44)

        result, conflict = self.combiner.combine(BpaOutput(sources=[
            source("a", first), source("b", second), source("c", third),
        ]))
        self.assertAlmostEqual(conflict, 0.44)
        self.assertEqual(len(result.combined_masses), 1)
        mass = result.combined_masses[0].combined_mass
        assert mass is not None
        self.assertAlmostEqual(mass, 1.0)

    def test_reduction_matches_direct_three_source_products(self):
        sources = [
            source("a", {self.x: 0.6, self.frame: 0.4}),
            source("b", {self.y: 0.3, self.frame: 0.7}),
            source("c", {self.x: 0.2, self.y: 0.5, self.frame: 0.3}),
        ]
        # Independent oracle: intersect every triple of original focal sets.
        unnormalized: MassFunction = {}
        conflict = 0.0
        for first, second, third in product(*(entry.masses for entry in sources)):
            intersection = (
                frozenset(first.hypotheses)
                & frozenset(second.hypotheses)
                & frozenset(third.hypotheses)
            )
            mass = first.mass * second.mass * third.mass
            if not intersection:
                conflict += mass
            else:
                unnormalized[intersection] = unnormalized.get(intersection, 0.0) + mass

        original = [entry.model_dump() for entry in sources]
        for ordered_sources in permutations(sources):
            with self.subTest(order=[entry.source for entry in ordered_sources]):
                result, k = self.combiner.combine(BpaOutput(sources=list(ordered_sources)))
                actual = {frozenset(entry.focal_set): entry.combined_mass for entry in result.combined_masses}
                self.assertAlmostEqual(k, conflict)
                self.assertEqual(actual.keys(), unnormalized.keys())
                for subset, mass in unnormalized.items():
                    value = actual[subset]
                    assert value is not None
                    self.assertAlmostEqual(value, mass / (1.0 - conflict))
        self.assertEqual([entry.model_dump() for entry in sources], original)

    def test_single_source_and_rounding_tolerance(self):
        entry = source("a", {self.x: 0.6000001, self.frame: 0.4})
        converted = to_mass_function(entry)
        self.assertAlmostEqual(fsum(converted.values()), 1.0)
        result, k = self.combiner.combine(BpaOutput(sources=[entry]))
        self.assertEqual(k, 0)
        self.assertEqual(
            {frozenset(mass.focal_set): mass.combined_mass for mass in result.combined_masses},
            converted,
        )

    def test_total_conflict_including_zero_mass_overlap(self):
        first = {self.x: 1.0, self.frame: 0.0}
        second = {self.y: 1.0}
        self.assertEqual(self.combiner.combine_two_sources(first, second), ({}, 1.0))
        with self.assertRaisesRegex(ValueError, "total conflict"):
            self.combiner.combine(BpaOutput(sources=[
                source("a", first), source("b", second),
                source("c", {self.frame: 1.0}),
            ]))

    def test_near_total_conflict_keeps_non_conflicting_mass(self):
        first = {self.x: 1.0 - 1e-14, self.frame: 1e-14}
        second = {self.y: 1.0}
        combined, _ = self.combiner.combine_two_sources(first, second)
        self.assertEqual(combined, {self.y: 1e-14})
        result, _ = self.combiner.combine(BpaOutput(sources=[
            source("a", first), source("b", second),
        ]))
        self.assertEqual(result.combined_masses[0].focal_set, {"y"})
        self.assertEqual(result.combined_masses[0].combined_mass, 1.0)

    def test_exactly_one_mass_field_and_registry(self):
        self.assertIs(CombinerRegistry._get("Dempster"), DempsterCombination)
        CombinedMass(focal_set={"x"}, combined_mass=0.0)
        CombinedMass(focal_set=set(), k=0.0)
        for values in ({}, {"combined_mass": 0.5, "k": 0.5}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                CombinedMass(focal_set={"x"}, **values)
