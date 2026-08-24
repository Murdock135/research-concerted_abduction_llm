from typing import Self

from concerted_abduction.llm.base import LanguageModel
from concerted_abduction.llm.registry import LanguageModelRegistry
from concerted_abduction.types import DataSample, FodOutput, FrameOfDiscernment
from concerted_abduction.utils.utils import load_prompt
from config.settings import ComponentConfig

from .base import FrameOfDiscernmentExtractor
from .registry import FodExtractorRegistry


@FodExtractorRegistry.register("language_model_fod_extractor")
class LanguageModelFodExtractor(FrameOfDiscernmentExtractor):
    """Language-model-based frame-of-discernment extractor.
    
    This extractor uses a language model to analyze multiple inputs and
    generate a frame for abductive reasoning. The system prompt can be
    customized to guide the LLM's output format and reasoning approach.
    
    Attributes:
        language_model: Configured language-model implementation to use.
    """

    def __init__(self, language_model: LanguageModel) -> None:
        self.language_model = language_model

    @classmethod
    def from_config(cls, cfg: ComponentConfig) -> Self:
        """Construct a frame-of-discernment extractor from configuration."""
        if cfg.llm is None:
            raise ValueError(
                f"FoD extractor {cfg.type!r} requires a language model. "
                "Please specify one in the configuration file."
            )
        if cfg.prompt_path is None:
            raise ValueError(
                f"FoD extractor {cfg.type!r} requires a prompt path. "
                "Please specify one in the configuration file."
            )

        language_model = LanguageModelRegistry.create(
            provider=cfg.llm.provider,
            model=cfg.llm.model_name,
            system_prompt=load_prompt(cfg.prompt_path),
        )

        return cls(language_model=language_model)

    def generate_frame(self, sample: DataSample) -> FodOutput:
        """Extract a frame of discernment from all responses in ``sample``."""

        prompt = (
            "Here are the inputs:\n"
            + "\n".join(
                f"{model_output.source}: {model_output.response}"
                for model_output in sample.outputs
            )
        )

        frame = self.language_model.generate(
            prompt,
            output_schema=FrameOfDiscernment,
        )
        if not isinstance(frame, FrameOfDiscernment):
            raise TypeError("Language model returned an unexpected output type")

        return FodOutput(
            hypotheses={output.source: output.response for output in sample.outputs},
            frame=frame,
        )
