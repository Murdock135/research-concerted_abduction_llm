from typing import TypeVar

from concerted_abduction.llm.base import LanguageModel

L = TypeVar('L', bound=LanguageModel)


class LanguageModelRegistry:
    _language_models: dict[str, type[LanguageModel]] = {}

    @classmethod
    def register(cls, name: str):
        """Register the Language Model object as the given name."""
        def wrapper(language_model: type[L]) -> type[L]:
            cls._language_models[name] = language_model
            return language_model
        
        return wrapper

    @classmethod
    def get(cls, name: str):
        """Return a registered language model"""
        if name not in cls._language_models:
            raise ValueError(
                f"Unknown language model: {name}. "
                f"Available language models: {cls.list_language_models()}"
            )

        return cls._language_models[name]

    @classmethod
    def list_language_models(cls):
        """List registered language models"""
        language_models = [f"{name}\n" for name in cls._language_models]
        return f"Language Models:\n{language_models}"
