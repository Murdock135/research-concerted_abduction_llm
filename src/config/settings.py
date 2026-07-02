"""
Settings.py

Loads environment variables and TOML-based configuration for pipeline
components (data generator, hypothesis extractor, ...). Configuration is
layered: bundled defaults in config/default_config.toml, optionally
overridden by a config.toml at the project root.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from concerted_abduction.utils.utils import find_project_root

PROJECT_ROOT = find_project_root(__file__)
DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_config.toml"
PROJECT_CONFIG_PATH = PROJECT_ROOT / "config.toml"
ENV_PATH = Path("~/.secrets/.llm_apis").expanduser()


# -----------------------------------------------------------------------
# Environment settings
# -----------------------------------------------------------------------
class ENVSettings(BaseSettings):
    """Loads API credentials from ~/.secrets/.llm_apis into the environment."""

    model_config = SettingsConfigDict(env_file=ENV_PATH, extra="ignore")

    gemini_api_key: Optional[str] = None

    def model_post_init(self, _) -> None:
        for key, val in self.model_dump().items():
            if val is not None:
                os.environ[key.upper()] = str(val)


# -----------------------------------------------------------------------
# Component settings (llm, prompts, examples, output)
# -----------------------------------------------------------------------
class LLMSetting(BaseModel):
    provider: str
    model_name: str = Field(..., alias="model")
    temperature: Optional[float] = None


class ComponentConfig(BaseModel):
    type: str = Field(..., description="Registry name of the implementation to use for this component")
    output_dir: Path
    llm: Optional[LLMSetting] = None
    prompt_path: Optional[Path] = None
    examples_path: Optional[Path] = None

    @field_validator("prompt_path", "examples_path", "output_dir", mode="before")
    @classmethod
    def resolve_path(cls, v: str | None) -> Path | None:
        if v is None:
            return v
        p = Path(v).expanduser()
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p


class ConcertedAbductionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file=[DEFAULT_CONFIG_PATH, PROJECT_CONFIG_PATH], extra="ignore"
    )

    data_generator: ComponentConfig
    hypothesis_extractor: ComponentConfig

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls, deep_merge=True),)
