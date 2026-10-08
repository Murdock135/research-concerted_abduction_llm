from collections.abc import Callable
from typing import TypeVar

from .base import Combiner

T = TypeVar("T", bound=Combiner)


class CombinerRegistry:
    """Registry of named evidence-combination implementations."""

    _combiners: dict[str, type[Combiner]] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[type[T]], type[T]]:
        """Register a combiner class under ``name``."""

        def wrapper(combiner_cls: type[T]) -> type[T]:
            if not issubclass(combiner_cls, Combiner):
                raise TypeError(
                    f"{combiner_cls.__name__} must inherit from Combiner"
                )
            if name in cls._combiners:
                raise ValueError(f"Combiner {name!r} is already registered")
            cls._combiners[name] = combiner_cls
            return combiner_cls

        return wrapper

    @classmethod
    def _get(cls, name: str) -> type[Combiner]:
        """Return the combiner class registered under ``name``."""
        if name not in cls._combiners:
            raise ValueError(
                f"Unknown combiner: {name!r}. "
                f"Available combiners: {cls.list_combiners()}"
            )
        return cls._combiners[name]

    @classmethod
    def list_combiners(cls) -> list[str]:
        """Return registered combiner names in deterministic order."""
        return sorted(cls._combiners)
