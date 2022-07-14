import json
from typing import List

from pydantic import BaseModel
from .enums import Lang, Vendor


class TranscriptionRequest(BaseModel):
    data_key: str
    s3_file_key: str
    file_key: str
    lang: Lang
    vendor: Vendor


class TranscriptionWord:
    def __init__(self, word: str, start_time: float, end_time: float):
        self.word = word
        self.start_time = start_time
        self.end_time = end_time

    @staticmethod
    def from_json(word):
        return TranscriptionWord(word['word'], word['start_time'], word['end_time'])


class Transcription:
    def __init__(self, transcripts: List[str], confidences: List[float], words: List[TranscriptionWord], vendor: str = None, alternatives: List['Transcription']=[]):
        self.transcripts = transcripts
        self.confidences = confidences
        self.words = words
        self.vendor = vendor
        self.alternatives = alternatives

    @staticmethod
    def from_json(transcription):
        return Transcription(transcription['transcripts'],
                             transcription['confidences'],
                             [TranscriptionWord.from_json(word) for word in transcription['words']],
                             transcription['vendor'],
                             [Transcription.from_json(alt) for alt in transcription.get('alternatives', [])])

    @property
    def obj(self):
        obj = {
            'transcripts': self.transcripts,
            'confidences': self.confidences,
            'words': list(map(lambda x: vars(x), self.words)),
            'vendor': self.vendor,
        }
        if self.alternatives:
            obj['alternatives'] = [alt.obj for alt in self.alternatives]

        return obj

    def tojson(self):
        return json.dumps(self.obj, ensure_ascii=False)
