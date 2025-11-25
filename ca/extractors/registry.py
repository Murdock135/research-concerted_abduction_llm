from typing import Dict, Type
from ca.extractors.base import HypothesisExtractor

class ExtractorRegistry:
    """
    ExtractorRegistry is the object that allows registering HypothesisExtractor objects, getting them and listing available ones.
    The list of Extractors are contained in a dict with the format {name: ExtractorObject}
    """
    _extractors: Dict[str, Type[HypothesisExtractor]] = {} 

    @classmethod
    def register(cls, name: str):
        """
        Register an extractor.
        """
        def wrapper(extractor_cls: Type[HypothesisExtractor]) -> Type[HypothesisExtractor]:
            # fail if an object of type HypothesisExtractor has not been supplied
            if not issubclass(extractor_cls, HypothesisExtractor):
                raise TypeError(f"{extractor_cls.__name__} must inherit from HypothesisExtractor")
            
            # append extractor_cls to _extractors
            cls._extractors[name] = extractor_cls
            return extractor_cls
        return wrapper

    @classmethod
    def get(cls, name: str):
        """Get a registered extractor by name."""
        if name not in cls._extractors:
            raise ValueError(f"Unknown extractor: {name}. Available extractors: {cls.list_extractors()}")
        
        return cls._extractors[name]

    @classmethod
    def list_extractors(cls):
        """Get the registered extractors."""
        return f"Extractors:\n{[f'{extractor}\n' for extractor in cls._extractors.keys()]}"        
