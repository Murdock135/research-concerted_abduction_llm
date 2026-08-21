from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass
class LanguageModel(ABC):
    model: str
    system_prompt: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temp: int = 0,
        top_p: int = 1,
        output_schema: type[BaseModel] | None = None,
    ) -> BaseModel | str:
        raise NotImplementedError
