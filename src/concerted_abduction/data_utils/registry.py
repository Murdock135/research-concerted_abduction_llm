from typing import Dict, Type, TypeVar
from concerted_abduction.data_utils.base import DataGenerator

T = TypeVar('T', bound=DataGenerator)

class DataGeneratorRegistry:
    """
    DataGeneratorRegistry is the object that allows registering DataGenerator objects, getting them and listing available ones.
    The list of Data Generators are contained in a dict with the format {name: DataGeneratorObject}
    """
    _generators: Dict[str, Type[DataGenerator]] = {}

    @classmethod
    def register(cls, name: str):
        """
        Register a data generator.
        """
        def wrapper(generator_cls: Type[T]) -> Type[T]:
            # fail if an object of type DataGenerator has not been supplied
            if not issubclass(generator_cls, DataGenerator):
                raise TypeError(f"{generator_cls.__name__} must inherit from DataGenerator")

            # append generator_cls to _generators
            cls._generators[name] = generator_cls
            return generator_cls
        return wrapper

    @classmethod
    def get(cls, name: str):
        """Get a registered data generator by name."""
        if name not in cls._generators:
            raise ValueError(f"Unknown data generator: {name}. Available generators: {cls.list_generators()}")

        return cls._generators[name]

    @classmethod
    def list_generators(cls):
        """Get the registered data generators."""
        return f"Data Generators:\n{[f'{generator}\n' for generator in cls._generators.keys()]}"
