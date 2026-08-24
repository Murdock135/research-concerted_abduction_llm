from typing import TypeVar

from concerted_abduction.focal_set.base import FocalSetCreator

T = TypeVar("T", bound=FocalSetCreator)


class FocalSetRegistry:
    """Registry of named focal-set creator implementations."""

    _creators: dict[str, type[FocalSetCreator]] = {}

    @classmethod
    def register(cls, name: str):
        """Register a focal-set creator under ``name``."""

        def wrapper(creator_cls: type[T]) -> type[T]:
            if not issubclass(creator_cls, FocalSetCreator):
                raise TypeError(f"{creator_cls.__name__} must inherit from FocalSetCreator")
            cls._creators[name] = creator_cls
            return creator_cls

        return wrapper

    @classmethod
    def _get(cls, name: str) -> type[FocalSetCreator]:
        """Get a registered focal-set creator by name."""
        if name not in cls._creators:
            raise ValueError(
                f"Unknown focal-set creator: {name}. "
                f"Available creators: {cls.list_creators()}"
            )
        return cls._creators[name]

    @classmethod
    def list_creators(cls) -> list[str]:
        """Return the names of all registered focal-set creators."""
        return list(cls._creators)
