from typing import Self

from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.llm.registry import LanguageModelRegistry
from concerted_abduction.types import FocalSetOutput, FodOutput
from concerted_abduction.utils.utils import load_prompt
from config.settings import ComponentConfig

from .base import FocalSetCreator
from .registry import FocalSetRegistry


@FocalSetRegistry.register("language_model_focal_set_creator")
class LanguageModelFocalSetCreator(FocalSetCreator):
    """Use a language model to derive focal sets for each evidence source.

    Given a ``FodOutput`` containing a frame of discernment and source texts,
    request a structured ``FocalSetOutput`` with subsets of frame hypotheses,
    justifications, and supporting verbatim citations grouped by source.

    Check that each input source appears exactly once, all returned hypotheses
    belong to the frame, and citations occur in their respective source texts.
    Record these validation issues in the returned output's
    ``validation_errors`` rather than raising an exception for them.

    Attributes:
        language_model: Configured language-model implementation used to
            generate focal sets. When constructed via ``from_config``, its
            system prompt is loaded from the configured prompt path.
    """

    def __init__(self, language_model: LanguageModel) -> None:
        self.language_model = language_model

    @classmethod
    def from_config(cls, cfg: ComponentConfig) -> Self:
        """Construct a focal-set creator from application configuration."""
        if cfg.llm is None:
            raise ValueError(
                f"Focal-set creator {cfg.type!r} requires a language model."
            )
        if cfg.prompt_path is None:
            raise ValueError(f"Focal-set creator {cfg.type!r} requires a prompt path.")

        language_model = LanguageModelRegistry.create(
            provider=cfg.llm.provider,
            model=cfg.llm.model_name,
            system_prompt=load_prompt(cfg.prompt_path),
        )
        return cls(language_model=language_model)

    def create_focal_sets(self, fod_output: FodOutput) -> FocalSetOutput:
        """Create focal sets and verify their hypotheses and source citations."""
        prompt = (
            "Create focal sets from this frame and source evidence:\n"
            f"{fod_output.model_dump_json(indent=2)}"
        )
        result = self.language_model.generate(prompt, output_schema=FocalSetOutput)
        if not isinstance(result, FocalSetOutput):
            raise TypeError("Language model returned an unexpected output type")

        result.validation_errors = self._validate_result(fod_output, result)
        return result

    @staticmethod
    def _validate_result(
        fod_output: FodOutput, result: FocalSetOutput
    ) -> list[str]:
        errors: list[str] = []
        expected_sources = set(fod_output.hypotheses)
        returned_sources = [source_result.source for source_result in result.sources]

        sources_unique = len(returned_sources) == len(set(returned_sources))
        sources_match = set(returned_sources) == expected_sources
        source_details = (
            f"Expected sources: {sorted(expected_sources)}\n"
            f"Returned sources: {returned_sources}"
        )
        if not sources_unique:
            errors.append(
                f"Focal-set output contains duplicate sources\n{source_details}"
            )
        if not sources_match:
            errors.append(
                "Focal-set output sources must exactly match the FoD output sources\n"
                f"{source_details}"
            )

        frame = set(fod_output.frame.frame)
        for source_result in result.sources:
            source_text = fod_output.hypotheses.get(source_result.source)
            for focal_set in source_result.focal_sets:
                unknown = set(focal_set.hypotheses) - frame
                if unknown:
                    errors.append(
                        f"Focal set for {source_result.source!r} contains hypotheses "
                        f"outside the frame: {sorted(unknown)}"
                    )
                if source_text is None:
                    continue
                for citation in focal_set.citations:
                    if citation not in source_text:
                        errors.append(
                            f"Citation for {source_result.source!r} is not a verbatim "
                            f"excerpt of its source text: {citation!r}"
                        )

        return errors
