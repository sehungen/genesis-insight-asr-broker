import abc

from .enums import Lang


class BaseTranscriber(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def transcribe(self, src: str, lang: Lang):
        pass
