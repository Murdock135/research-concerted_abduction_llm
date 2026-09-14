import json
from typing import Self

from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.llm.registry import LanguageModelRegistry

from concerted_abduction.types import (
    BpaOutput, FocalSetOutput, FodOutput, SourceBpa, SourceMassResponse,
)
from concerted_abduction.utils.utils import load_prompt
from config.settings import ComponentConfig

from .base import BpaAssigner
from .registry import BpaRegistry


@BpaRegistry.register("language_model_bpa_assigner")
class LanguageModelBpaAssigner(BpaAssigner):
    """Heuristic LLM masses with validation of the generated BPA.

    Focal-set diagnostics belong to the upstream creator and are excluded from
    the prompt without revalidation. Invalid BPA distributions raise ValueError;
    no silent normalization occurs. Unlisted subsets implicitly have zero mass.
    """

    def __init__(self, language_model: LanguageModel) -> None:
        self.language_model = language_model

    @classmethod
    def from_config(cls, cfg: ComponentConfig) -> Self:
        """Construct the language model using the configured provider and prompt."""
        if cfg.llm is None or cfg.prompt_path is None:
            raise ValueError(f"BPA assigner {cfg.type!r} requires llm and prompt_path")

        return cls(
            LanguageModelRegistry.create(
                provider=cfg.llm.provider,
                model=cfg.llm.model_name,
                system_prompt=load_prompt(cfg.prompt_path),
            )
        )

    def assign_masses(
        self, fod_output: FodOutput, focal_set_output: FocalSetOutput
    ) -> BpaOutput:
        """Ask the LLM for per-source masses, then validate its assignments."""

        frame_labels = fod_output.frame.frame
        frame = frozenset(frame_labels)

        if not frame or len(frame) != len(frame_labels) or any(
            not label.strip() for label in frame_labels
        ):
            raise ValueError("Frame must contain unique, non-blank hypotheses")
        if not fod_output.hypotheses:
            raise ValueError("BPA requires at least one input source")

        source_bpas: list[SourceBpa] = []
        for source, response in fod_output.hypotheses.items():
            focal_sets = [
                focal
                for entry in focal_set_output.sources if entry.source == source
                for focal in entry.focal_sets
                if focal.hypotheses and frozenset(focal.hypotheses) <= frame
            ]
            allowed = {frozenset(focal.hypotheses) for focal in focal_sets}
            allowed.add(frame)

            prompt = (
                "Assign a basic probability assignment to this source's evidence. "
                "Return masses containing hypotheses, mass, and justification. "
                "Use only supplied focal sets or the full frame; omitted subsets "
                "have zero mass. Masses must sum to one.\n"
                + json.dumps({
                    "source": source,
                    "response": response,
                    "frame": frame_labels,
                    "focal_sets": [focal.model_dump() for focal in focal_sets],
                }, ensure_ascii=False, indent=2)
            )
            result = self.language_model.generate(
                prompt, output_schema=SourceMassResponse
            )
            if not isinstance(result, SourceMassResponse):
                raise TypeError("Language model returned an unexpected BPA output type")
            # Revalidate even if a provider returns a preconstructed model.
            result = SourceMassResponse.model_validate(result.model_dump())
            for mass in result.masses:
                subset = frozenset(mass.hypotheses)
                if not subset <= frame:
                    raise ValueError(f"BPA subset for {source!r} is outside the frame")
                if subset not in allowed:
                    raise ValueError(
                        f"BPA subset for {source!r} must be an input focal "
                        "set or the full frame"
                    )

            # Python owns the source; SourceBpa validates duplicates and totals.
            source_bpas.append(SourceBpa(source=source, masses=result.masses))

        return BpaOutput(sources=source_bpas)
