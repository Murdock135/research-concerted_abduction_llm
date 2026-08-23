from collections.abc import Callable
from typing import TypeVar

from concerted_abduction.llm.base import LanguageModel

L = TypeVar("L", bound=LanguageModel)


class LanguageModelRegistry:
    _providers: dict[str, type[LanguageModel]] = {}

    @classmethod
    def register(cls, provider: str) -> Callable[[type[L]], type[L]]:
        """Register a language-model implementation for a provider."""
        def wrapper(language_model_cls: type[L]) -> type[L]:
            if provider in cls._providers:
                raise ValueError(f"Provider {provider!r} is already registered")

            cls._providers[provider] = language_model_cls
            return language_model_cls

        return wrapper

    @classmethod
    def _get(cls, provider: str) -> type[LanguageModel]:
        """Return the language-model class registered for a provider."""
        if provider not in cls._providers:
            available = ", ".join(cls.list_providers()) or "(none registered)"
            raise ValueError(
                f"Unknown language model provider: {provider!r}. "
                f"Available providers: {available}"
            )

        return cls._providers[provider]

    @classmethod
    def create(
        cls,
        provider: str,
        model: str,
        system_prompt: str = "",
    ) -> LanguageModel:
        """Create a LanguageModel object"""
        language_model_cls = cls._get(provider)

        return language_model_cls(
            model=model,
            system_prompt=system_prompt,
        )

    @classmethod
    def list_providers(cls) -> list[str]:
        """List registered language-model providers."""
        return sorted(cls._providers)
