from typing import TypeVar

from .base import BpaAssigner

T = TypeVar("T", bound=BpaAssigner)


class BpaRegistry:
    _assigners: dict[str, type[BpaAssigner]] = {}

    @classmethod
    def register(cls, name: str):
        def wrapper(assigner_cls: type[T]) -> type[T]:
            if not issubclass(assigner_cls, BpaAssigner):
                raise TypeError("BPA implementations must inherit from BpaAssigner")
            if name in cls._assigners:
                raise ValueError(f"BPA assigner {name!r} is already registered")
            cls._assigners[name] = assigner_cls
            return assigner_cls
        return wrapper

    @classmethod
    def _get(cls, name: str) -> type[BpaAssigner]:
        if name not in cls._assigners:
            raise ValueError(f"Unknown BPA assigner: {name}. Available: {cls.list_assigners()}")
        return cls._assigners[name]

    @classmethod
    def list_assigners(cls) -> list[str]:
        return sorted(cls._assigners)
