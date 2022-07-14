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

    def make_request_and_response(self, transcriber: BaseTranscriber, s3_file_key: str, data_key: str, lang: Lang, use_webhook: bool):
        # 음성인식 요청
        def __request_fn():
            return data_key, transcriber.transcribe(s3_file_key, lang)

        # 음성인식 응답 - 동기
        def __response_fn(_future: Future):
            data_key_from_request, transcription = _future.result()
            transcription_text = '' if transcription is None else transcription.tojson()
            self.__redis.set(data_key_from_request, transcription_text, ex=self.__live_timeout)

        # 음성인식 응답 - 비동기(웹훅)
        def __webhook_response_fn(_future: Future):
            data_key_from_request, token = _future.result()
            if token:
                # 토큰이 있다면 토큰 등록 후, 나중에 결과를 찾기 위한 토큰과 data_key 등록
                self.__redis.set(f'transcriber-webhook:{token}', data_key_from_request, ex=self.__live_timeout)
            else:
                # 토큰 반환이 None 이라면 실패한것으로 간주
                self.__redis.set(data_key_from_request, '', ex=self.__live_timeout)

        return __request_fn, __webhook_response_fn if use_webhook else  __response_fn

    def poll(self):
        while True:
            req = self.__redis.lpop('trans-broker-queue')
            if not req:
                time.sleep(1)
                continue

            req = TranscriptionRequest.parse_obj(orjson.loads(req.decode()))

            if req.vendor in self.__transcribers:
                use_webhook, transcriber = self.__transcribers[req.vendor]
                request_fn, response_fn = self.make_request_and_response(transcriber, req.s3_file_key, req.data_key, req.lang, use_webhook)
                self.__requester.submit(request_fn, response_fn)
            else:
                # Transcriber 없음
                self.__redis.set(req.data_key, '')
