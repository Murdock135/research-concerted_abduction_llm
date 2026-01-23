from concerted_abduction.types import DataSet

from typing import Optional

class DataGenerator:
    def __init__(self, n_samples: int, n_models: int, conflict_config: dict, system_prompt: Optional[str] = None) -> None:
        self.n_samples = n_samples
        self.n_models = n_models
        self.conflict_config = conflict_config
        self.system_prompt = system_prompt