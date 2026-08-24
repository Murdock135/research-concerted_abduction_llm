import unittest

from pydantic import BaseModel

from concerted_abduction.focal_set import FocalSetCreator, FocalSetRegistry
from concerted_abduction.focal_set.llm import LanguageModelFocalSetCreator
from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.types import (
    FocalSet,
    FocalSetOutput,
    FodOutput,
    FrameOfDiscernment,
    SourceFocalSets,
)


class StubLanguageModel(LanguageModel):
    response: BaseModel | str

    def __init__(self, response: BaseModel | str) -> None:
        super().__init__(model="stub")
        self.response = response

    def generate(
        self,
        prompt: str,
        temp: int = 0,
        top_p: int = 1,
        output_schema: type[BaseModel] | None = None,
    ) -> BaseModel | str:
        return self.response


def make_fod_output() -> FodOutput:
    return FodOutput(
        hypotheses={"model-a": "The findings suggest migraine or tension headache."},
        frame=FrameOfDiscernment(frame=["migraine", "tension headache"]),
    )


class LanguageModelFocalSetCreatorTests(unittest.TestCase):
    def test_creator_is_registered(self) -> None:
        creator_cls = FocalSetRegistry._get("language_model_focal_set_creator")
        self.assertTrue(issubclass(creator_cls, FocalSetCreator))

    def test_returns_cited_focal_sets(self) -> None:
        response = FocalSetOutput(
            sources=[
                SourceFocalSets(
                    source="model-a",
                    focal_sets=[
                        FocalSet(
                            hypotheses=["migraine", "tension headache"],
                            justification="The source presents an unresolved alternative.",
                            citations=["migraine or tension headache"],
                        )
                    ],
                )
            ]
        )
        creator = LanguageModelFocalSetCreator(StubLanguageModel(response))

        self.assertEqual(creator.create_focal_sets(make_fod_output()), response)

    def test_preserves_hypothesis_outside_frame_with_validation_error(self) -> None:
        response = FocalSetOutput(
            sources=[
                SourceFocalSets(
                    source="model-a",
                    focal_sets=[
                        FocalSet(
                            hypotheses=["cluster headache"],
                            justification="The source supports it.",
                            citations=["findings suggest"],
                        )
                    ],
                )
            ]
        )
        creator = LanguageModelFocalSetCreator(StubLanguageModel(response))

        result = creator.create_focal_sets(make_fod_output())

        self.assertEqual(result.sources, response.sources)
        self.assertEqual(len(result.validation_errors), 1)
        self.assertIn("outside the frame", result.validation_errors[0])

    def test_preserves_non_verbatim_citation_with_validation_error(self) -> None:
        response = FocalSetOutput(
            sources=[
                SourceFocalSets(
                    source="model-a",
                    focal_sets=[
                        FocalSet(
                            hypotheses=["migraine"],
                            justification="The source supports migraine.",
                            citations=["This quote was invented"],
                        )
                    ],
                )
            ]
        )
        creator = LanguageModelFocalSetCreator(StubLanguageModel(response))

        result = creator.create_focal_sets(make_fod_output())

        self.assertEqual(result.sources, response.sources)
        self.assertEqual(len(result.validation_errors), 1)
        self.assertIn("not a verbatim excerpt", result.validation_errors[0])

    def test_collects_multiple_validation_errors(self) -> None:
        response = FocalSetOutput(
            sources=[
                SourceFocalSets(
                    source="unexpected-source",
                    focal_sets=[
                        FocalSet(
                            hypotheses=["unknown hypothesis"],
                            justification="Unsupported output.",
                            citations=["invented citation"],
                        )
                    ],
                )
            ]
        )
        creator = LanguageModelFocalSetCreator(StubLanguageModel(response))

        result = creator.create_focal_sets(make_fod_output())

        self.assertEqual(result.sources, response.sources)
        self.assertEqual(len(result.validation_errors), 2)
        self.assertTrue(
            any("must exactly match" in error for error in result.validation_errors)
        )
        self.assertTrue(
            any("outside the frame" in error for error in result.validation_errors)
        )


if __name__ == "__main__":
    unittest.main()
