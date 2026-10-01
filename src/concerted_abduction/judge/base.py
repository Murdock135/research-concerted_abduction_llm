from abc import ABC, abstractmethod

from pathlib import Path

# TODO:
# 1. Define output schema
# 2. Implement deep-agents version

class Judge(ABC):
    @abstractmethod
    def judge(self, prompt: str, materials: list[Path]):
        ...
    