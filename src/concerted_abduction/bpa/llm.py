import json
from typing import Self

from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.llm.registry import LanguageModelRegistry
from concerted_abduction.types import BpaOutput, FocalSetOutput, FodOutput
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
        frame = frozenset(fod_output.frame.frame)
        sources = set(fod_output.hypotheses.keys())

        # Each source can receive mass on its extracted focal sets or on the
        # full frame (ignorance). Frozensets make hypothesis order irrelevant
        # and allow these groups to be stored inside another set.
        # A source without extracted focal sets can still receive full ignorance.
        allowed: dict[str, set[frozenset[str]]] = {
            source: {frame} for source in sources
        }
        for entry in focal_set_output.sources:
            # Start a new source with the full frame, then add its focal sets.
            allowed.setdefault(entry.source, {frame}).update(
                frozenset(focal.hypotheses) for focal in entry.focal_sets
            )

        # Include original evidence and extracted groups, leaving upstream
        # validation diagnostics out of the LLM context.
        prompt = (
            "Assign per-source basic probability assignments to this evidence:\n"
            + json.dumps(
                {
                    "fod_output": fod_output.model_dump(),
                    "focal_sets": [
                        entry.model_dump() for entry in focal_set_output.sources
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

        # The LLM chooses the masses; Python checks the resulting distribution.
        result = self.language_model.generate(prompt, output_schema=BpaOutput)
        if not isinstance(result, BpaOutput):
            raise TypeError("Language model returned an unexpected BPA output type")

        # Apply mass bounds, per-source totals, and uniqueness checks even when
        # the provider returns a preconstructed model. Do not normalize masses.
        result = BpaOutput.model_validate(result.model_dump())

        # Check source coverage and group membership against this scenario;
        # these constraints require context beyond the output schema alone.
        if {entry.source for entry in result.sources} != set(sources):
            raise ValueError("BPA sources must exactly match input sources")

        for entry in result.sources:
            for mass in entry.masses:
                subset = frozenset(mass.hypotheses)

                if not subset <= frame:
                    raise ValueError(
                        f"BPA subset for {entry.source!r} is outside the frame"
                    )

                if subset not in allowed[entry.source]:
                    raise ValueError(
                        f"BPA subset for {entry.source!r} must be an input focal "
                        "set or the full frame"
                    )

        return result
