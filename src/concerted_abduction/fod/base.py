from abc import ABC, abstractmethod

from concerted_abduction.types import DataSample, FodOutput


class FrameOfDiscernmentExtractor(ABC):
    """Base class for frame-of-discernment extractors."""

    @abstractmethod
    def generate_frame(self, sample: DataSample) -> FodOutput:
        """Generate a frame of discernment from a data sample."""
        ...
