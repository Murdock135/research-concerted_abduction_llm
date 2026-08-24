from typing import TypeVar

from concerted_abduction.fod.base import FrameOfDiscernmentExtractor

T = TypeVar('T', bound=FrameOfDiscernmentExtractor)

class FodExtractorRegistry:
    """Registry of named frame-of-discernment extractor implementations."""
    _extractors: dict[str, type[FrameOfDiscernmentExtractor]] = {} 

    @classmethod
    def register(cls, name: str):
        """Register an extractor under ``name``."""
        def wrapper(extractor_cls: type[T]) -> type[T]:
            if not issubclass(extractor_cls, FrameOfDiscernmentExtractor):
                raise TypeError(f"{extractor_cls.__name__} must inherit from FrameOfDiscernmentExtractor")
            
            cls._extractors[name] = extractor_cls
            return extractor_cls
        return wrapper

    @classmethod
    def _get(cls, name: str) -> type[FrameOfDiscernmentExtractor]:
        """Get a registered extractor by name."""
        if name not in cls._extractors:
            raise ValueError(
                f"Unknown FoD extractor: {name}. "
                f"Available extractors: {cls.list_extractors()}"
            )
        
        return cls._extractors[name]

    @classmethod
    def list_extractors(cls) -> list[str]:
        """Return the names of all registered extractors."""
        return list(cls._extractors)
