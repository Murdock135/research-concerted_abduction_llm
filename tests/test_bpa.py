import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

from concerted_abduction.bpa import BpaRegistry, LanguageModelBpaAssigner
from concerted_abduction.types import (
    BpaOutput, FocalSet, FocalSetMass, FocalSetOutput, FodOutput,
    FrameOfDiscernment, SourceBpa, SourceFocalSets,
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
        self.lm.generate.return_value = distribution()
        self.assigner = LanguageModelBpaAssigner(self.lm)

    def test_valid_assignment_and_context(self):
        result = self.assigner.assign_masses(self.fod, self.focal)
        self.assertEqual(result, distribution())
        self.assertIn("Probably x", self.lm.generate.call_args.args[0])
        self.assertIs(self.lm.generate.call_args.kwargs["output_schema"], BpaOutput)
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

    def test_disallowed_output_subset(self):
        for subset in [["y"], ["unknown"]]:
            self.lm.generate.return_value = distribution(subset=subset)
            with self.subTest(subset=subset), self.assertRaises(ValueError):
                self.assigner.assign_masses(self.fod, self.focal)

    def test_output_source_mismatch(self):
        result = distribution()
        result.sources[0].source = "other"
        self.lm.generate.return_value = result
        with self.assertRaisesRegex(ValueError, "sources"):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_focal_diagnostics_and_paraphrases_do_not_block_assignment(self):
        self.focal.validation_errors = ["Citation is not a verbatim excerpt"]
        self.focal.sources[0].focal_sets[0].citations = ["x is probable"]
        before = self.focal.model_dump()

        self.assertEqual(self.assigner.assign_masses(self.fod, self.focal), distribution())

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
        self.assertEqual(self.assigner.assign_masses(self.fod, self.focal), distribution())
        self.lm.generate.assert_called_once()

    def test_bpa_output_must_still_belong_to_frame(self):
        self.focal.sources[0].focal_sets[0].hypotheses = ["unknown"]
        self.lm.generate.return_value = distribution(subset=["unknown"])
        with self.assertRaisesRegex(ValueError, "outside the frame"):
            self.assigner.assign_masses(self.fod, self.focal)
        self.lm.generate.assert_called_once()

    def test_vacuous_assignment(self):
        self.lm.generate.return_value = BpaOutput(sources=[SourceBpa(source="a", masses=[
            FocalSetMass(hypotheses=["y", "x"], mass=1, justification="Ignorance")
        ])])
        self.assertEqual(self.assigner.assign_masses(self.fod, self.focal).sources[0].masses[0].mass, 1)

    def test_unexpected_provider_output(self):
        self.lm.generate.return_value = "bad"
        with self.assertRaises(TypeError):
            self.assigner.assign_masses(self.fod, self.focal)

    def test_missing_focal_source_can_receive_full_ignorance(self):
        self.focal.sources = []
        self.lm.generate.return_value = BpaOutput(sources=[SourceBpa(
            source="a", masses=[FocalSetMass(
                hypotheses=["x", "y"], mass=1, justification="Ignorance"
            )]
        )])
        result = self.assigner.assign_masses(self.fod, self.focal)
        self.assertEqual(result.sources[0].masses[0].mass, 1)


if __name__ == "__main__":
    unittest.main()
