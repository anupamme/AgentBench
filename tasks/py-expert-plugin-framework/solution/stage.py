from abc import ABC, abstractmethod


class Stage(ABC):
    @abstractmethod
    def process(self, data: list) -> list:
        pass
