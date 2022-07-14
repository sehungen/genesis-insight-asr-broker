from concurrent.futures import Future
from typing import Dict, Any, Tuple
from redis import StrictRedis

from transcribers import BaseTranscriber
from transcribers import Vendor, Lang, TranscriptionRequest
from downloader.base_downloader import BaseDownloader

import orjson
import time

from .executor import ParallelExecutor


class TranscriptionRequestRunner:
    def __init__(self, redis: StrictRedis, transcribers: Dict[Vendor, Tuple[bool, Any]], requester: ParallelExecutor, downloader: BaseDownloader, tempdir: str, live_timeout=60 * 60 * 24):
        self.__redis = redis
        self.__transcribers = transcribers
        self.__requester = requester
        self.__live_timeout = live_timeout
        self.__downloader = downloader
        self.__tempdir = tempdir

    def make_request_and_response(self, transcriber: BaseTranscriber, s3_file_key: str, data_key: str, lang: Lang, use_s3_directly: bool):
        # 음성인식 요청
        def __request_fn():
            return data_key, transcriber.transcribe(s3_file_key, lang)

        # 음성인식 응답
        def __response_fn(_future: Future):
            data_key_from_request, transcription = _future.result()
            transcription_text = '' if transcription is None else transcription.tojson()
            self.__redis.set(data_key_from_request, transcription_text, ex=self.__live_timeout)
        return __request_fn, __response_fn

    def poll(self):
        while True:
            req = self.__redis.lpop('trans-broker-queue')
            if not req:
                time.sleep(1)
                continue

            req = TranscriptionRequest.parse_obj(orjson.loads(req.decode()))

            if req.vendor in self.__transcribers:
                use_s3_directly, transcriber = self.__transcribers[req.vendor]
                request_fn, response_fn = self.make_request_and_response(transcriber, req.s3_file_key, req.data_key, req.lang, use_s3_directly)
                self.__requester.submit(request_fn, response_fn)
            else:
                # Transcriber 없음
                self.__redis.set(req.data_key, '')
