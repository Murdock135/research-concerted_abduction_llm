from typing import TypeVar

from .base import EvidenceCombiner

T = TypeVar("T", bound=EvidenceCombiner)


class CombinerRegistry:
    _combiners: dict[str, type[EvidenceCombiner]] = {}

    @classmethod
    def register(cls, name: str):
        def wrapper(combiner_cls: type[T]) -> type[T]:
            if not name.strip():
                raise ValueError("Combiner name must not be blank")
            if not issubclass(combiner_cls, EvidenceCombiner):
                raise TypeError("Combiners must inherit from EvidenceCombiner")
            if name in cls._combiners:
                raise ValueError(f"Combiner {name!r} is already registered")
            cls._combiners[name] = combiner_cls
            return combiner_cls
        return wrapper

    @classmethod
    def _get(cls, name: str) -> type[EvidenceCombiner]:
        if name not in cls._combiners:
            raise ValueError(f"Unknown combiner: {name}. Available: {cls.list_combiners()}")
        return cls._combiners[name]

    @classmethod
    def list_combiners(cls) -> list[str]:
        return sorted(cls._combiners)
