import json
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from concerted_abduction.bpa import BpaRegistry, LanguageModelBpaAssigner
from concerted_abduction.types import (
    BpaOutput, FocalSet, FocalSetMass, FocalSetOutput, FodOutput,
    FrameOfDiscernment, SourceBpa, SourceFocalSets, SourceMassResponse,
)
from config.settings import ConcertedAbductionSettings


def distribution(mass=0.7, subset=None):
    return BpaOutput(sources=[SourceBpa(source="a", masses=[
        FocalSetMass(hypotheses=subset or ["x"], mass=mass, justification="Support"),
        FocalSetMass(hypotheses=["x", "y"], mass=1-mass, justification="Ignorance"),
    ])])


class BpaTests(unittest.TestCase):
    def setUp(self):
        self.fod = FodOutput(hypotheses={"a": "Probably x"},
                             frame=FrameOfDiscernment(frame=["x", "y"]))
        self.focal = FocalSetOutput(sources=[SourceFocalSets(source="a", focal_sets=[
            FocalSet(hypotheses=["x"], justification="Support", citations=["Probably x"])
        ])])
        self.lm = Mock()
        self.lm.generate.return_value = SourceMassResponse(masses=[
            FocalSetMass(hypotheses=["x"], mass=0.7, justification="Support"),
            FocalSetMass(hypotheses=["x", "y"], mass=0.3, justification="Ignorance"),
        ])
        self.assigner = LanguageModelBpaAssigner(self.lm)

    def test_valid_assignment_and_context(self):
        result = self.assigner.assign_masses(self.fod, self.focal)
        self.assertAlmostEqual(result.sources[0].masses[0].mass, 0.7)
        self.assertIn("Probably x", self.lm.generate.call_args.args[0])
        self.assertIs(self.lm.generate.call_args.kwargs["output_schema"], SourceMassResponse)
        self.assertEqual(BpaOutput.model_validate_json(result.model_dump_json()), result)

    def test_default_configuration(self):
        settings = ConcertedAbductionSettings()  # pyright: ignore[reportCallIssue]
        self.assertIs(BpaRegistry._get(settings.bpa.type), LanguageModelBpaAssigner)
        self.assertTrue(settings.bpa.prompt_path and settings.bpa.prompt_path.is_file())
        with patch("concerted_abduction.bpa.llm.LanguageModelRegistry.create", return_value=self.lm):
            self.assertIs(LanguageModelBpaAssigner.from_config(settings.bpa).language_model, self.lm)

    def test_invalid_mass_values(self):
        for mass in [-0.1, 1.1, float("nan"), float("inf")]:
            with self.subTest(mass=mass), self.assertRaises(ValidationError):
                FocalSetMass(hypotheses=["x"], mass=mass, justification="test")

    def test_invalid_distributions(self):
        for entries in [
            [(["x"], 0.8)],
            [(["x", "y"], 0.5), (["y", "x"], 0.5)],
            [([], 1)],
            [(["x", "x"], 1)],
        ]:
            with self.subTest(entries=entries), self.assertRaises(ValidationError):
                SourceBpa(source="a", masses=[FocalSetMass(hypotheses=h, mass=m, justification="test") for h, m in entries])

    def test_disallowed_subsets(self):
        for subset in [["unknown"], ["y"]]:
            self.lm.generate.return_value.masses[0].hypotheses = subset
            with self.subTest(subset=subset), self.assertRaises(ValueError):
                self.assigner.assign_masses(self.fod, self.focal)

    def test_duplicate_generated_subsets(self):
        self.lm.generate.return_value.masses[0].hypotheses = ["y", "x"]
        with self.assertRaisesRegex(ValueError, "Duplicate mass subsets"):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_preconstructed_response_is_revalidated(self):
        self.lm.generate.return_value.masses[0].mass = float("nan")
        with self.assertRaises(ValidationError):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_invalid_generated_total(self):
        self.lm.generate.return_value.masses[0].mass = 0.8
        with self.assertRaisesRegex(ValueError, "sum to one"):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_calls_are_per_source_and_evidence_is_isolated(self):
        self.fod.hypotheses["b"] = "Definitely y"
        self.focal.sources.append(SourceFocalSets(source="b", focal_sets=[
            FocalSet(hypotheses=["y"], justification="Support b", citations=["Definitely y"])
        ]))
        second = SourceMassResponse(masses=[
            FocalSetMass(hypotheses=["y"], mass=1, justification="Support b")
        ])
        self.lm.generate.side_effect = [self.lm.generate.return_value, second]
        result = self.assigner.assign_masses(self.fod, self.focal)
        self.assertEqual([entry.source for entry in result.sources], ["a", "b"])
        self.assertEqual(result.sources[1].masses, second.masses)
        self.assertEqual(self.lm.generate.call_count, 2)
        first_call, second_call = self.lm.generate.call_args_list
        first_context = json.loads(first_call.args[0].split("\n", 1)[1])
        second_context = json.loads(second_call.args[0].split("\n", 1)[1])
        self.assertEqual(first_context["source"], "a")
        self.assertEqual(second_context["source"], "b")
        self.assertNotIn("Definitely y", first_call.args[0])
        self.assertNotIn("Probably x", second_call.args[0])
        self.assertEqual(second_context["focal_sets"][0]["hypotheses"], ["y"])

    def test_empty_response_is_rejected(self):
        self.lm.generate.return_value.masses = []
        with self.assertRaises(ValidationError):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_focal_diagnostics_and_paraphrases_do_not_block_assignment(self):
        self.focal.validation_errors = ["Citation is not a verbatim excerpt"]
        self.focal.sources[0].focal_sets[0].citations = ["x is probable"]
        before = self.focal.model_dump()

        self.assertEqual(self.assigner.assign_masses(self.fod, self.focal).sources[0].source, "a")

        self.lm.generate.assert_called_once()
        prompt = self.lm.generate.call_args.args[0]
        self.assertIn("x is probable", prompt)
        self.assertIn("Probably x", prompt)
        self.assertNotIn("validation_errors", prompt)
        self.assertNotIn("Citation is not a verbatim excerpt", prompt)
        self.assertEqual(self.focal.model_dump(), before)

    def test_upstream_subsets_are_not_revalidated(self):
        self.focal.sources[0].focal_sets.append(FocalSet(
            hypotheses=["unknown"], justification="Upstream issue", citations=["paraphrase"]
        ))
        self.assertEqual(self.assigner.assign_masses(self.fod, self.focal).sources[0].source, "a")
        self.lm.generate.assert_called_once()

    def test_source_is_filled_from_input(self):
        self.fod.hypotheses = {"Source with a long name": "Probably x"}
        self.focal.sources[0].source = "Source with a long name"
        result = self.assigner.assign_masses(self.fod, self.focal)
        self.assertEqual(result.sources[0].source, "Source with a long name")
        self.assertEqual(result.sources[0].masses[0].hypotheses, ["x"])
        self.assertEqual(result.sources[0].masses[1].hypotheses, ["x", "y"])

    def test_vacuous_assignment(self):
        self.lm.generate.return_value = SourceMassResponse(masses=[
            FocalSetMass(hypotheses=["x", "y"], mass=1, justification="Ignorance")
        ])
        self.assertEqual(self.assigner.assign_masses(self.fod, self.focal).sources[0].masses[0].mass, 1)

    def test_full_frame_is_allowed_in_any_order(self):
        self.focal.sources[0].focal_sets = [FocalSet(
            hypotheses=["y", "x"], justification="Uncertain", citations=["Probably"]
        )]
        self.lm.generate.return_value = SourceMassResponse(masses=[
            FocalSetMass(hypotheses=["y", "x"], mass=1, justification="Ignorance")
        ])
        result = self.assigner.assign_masses(self.fod, self.focal)
        context = json.loads(self.lm.generate.call_args.args[0].split("\n", 1)[1])
        self.assertEqual(context["frame"], ["x", "y"])
        self.assertEqual(result.sources[0].masses[0].hypotheses, ["y", "x"])

    def test_unexpected_provider_output(self):
        self.lm.generate.return_value = "bad"
        with self.assertRaises(TypeError):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_missing_focal_source_can_receive_full_ignorance(self):
        self.focal.sources = []
        self.lm.generate.return_value = SourceMassResponse(masses=[
            FocalSetMass(hypotheses=["y", "x"], mass=1, justification="Ignorance")
        ])
        result = self.assigner.assign_masses(self.fod, self.focal)
        self.assertEqual(result.sources[0].masses[0].mass, 1)


if __name__ == "__main__":
    unittest.main()
