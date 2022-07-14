import datetime
import json
import time
import abc

from typing import Callable

from downloader.base_downloader import BaseDownloader
from transcribers import Lang, Vendor, Transcription


def create_file_key(filename: str, unique_key: str):
    return f'trans-context/{unique_key}/{filename}'


def create_s3_file_key(filename: str, unique_key: str, unique_key2: str):
    return f'trans-context/{unique_key}/{unique_key2}/{filename}'


def create_data_key(filename: str, unique_key: str, lang: Lang, vendor: Vendor):
    return f'trans-context:{filename}:{unique_key}:{lang.value}:{vendor.value}'


class RedisBuilder(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def redis_lock(self) -> Callable:
        return lambda: ()

    @property
    @abc.abstractmethod
    def redis(self) -> Callable:
        return lambda: ()


class TranscriptionContext:
    def __init__(self, builder: RedisBuilder, downloader, filename: str, unique_key: str, unique_key2: str):
        self.__builder = builder
        self.__redis = builder.redis()
        self.__downloader = downloader
        self.__filename = filename
        self.__unique_key = unique_key
        self.__unique_key2 = unique_key2
        self.__file_lock = builder.redis_lock(self.__redis, self.file_key)

    @property
    def filename(self):
        return self.__filename

    @property
    def unique_key2(self):
        return self.__unique_key2

    @property
    def unique_key(self):
        return self.__unique_key

    @property
    def file_key(self):
        return create_file_key(self.filename, self.unique_key)

    @property
    def s3_file_key(self):
        return create_s3_file_key(self.filename, self.unique_key, self.unique_key2)

    def __enter__(self):
        self.__file_lock.acquire()
        # self._upload_to_storage(self.filename, self.s3_file_key)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup_storage(self.s3_file_key)
        self.__file_lock.release()

    def _upload_to_storage(self, local_filename, remote_filename):
        print(f'Upload - {remote_filename}')
        self.__downloader.upload_file(local_filename, remote_filename)

    def _cleanup_storage(self, remote_filename):
        print(f'Cleanup - {remote_filename}')
        try:
            self.__downloader.delete_file(remote_filename)
        except:
            # 파일 삭제 예외 무시
            pass

    def _check_storage(self, remote_filename):
        print(f'Check - {remote_filename}')
        try:
            return self.__downloader.check_file(remote_filename)
        except:
            pass
        return False

    def _request_to_process(self, data_key: str, lang: Lang, vendor: Vendor):
        pydict = {
            'data_key': data_key,
            's3_file_key': self.s3_file_key,
            'file_key': self.file_key,
            'lang': lang.value,
            'vendor': vendor.value
        }
        self.__redis.lpush('trans-broker-queue', json.dumps(pydict))

    def _wait_for_response(self, key, timeout=60):
        # 값 폴링
        for _ in range(timeout):
            if key in self.__redis:
                break
            time.sleep(1)
        data = self.__redis.get(key)
        return data if data else b''

    def _hit(self, data_key):
        return self.__redis.get(data_key)

    def transcribe(self, vendor: Vendor = Vendor.AWS, lang: Lang = Lang.LANG_KO) -> Transcription:
        # 음성 변환 결과에 대한 락 - 동일한 오디오 파일, 동일한 언어, 동일한 벤더의 결과의 요청에 대해서 대기한다.
        # 락의 최대 대기 시간은 20분이다.
        data_key = create_data_key(self.filename, self.unique_key, lang, vendor)
        with self.__builder.redis_lock(self.__redis, data_key, expire=60 * 20):
            # 음성 변환 결과에 대한 락이 풀리고 결과가 이미 hit 됬는지 확인 하고 hit 됬다면 바로 반환
            result = self._hit(data_key)
            if result:
                return Transcription.from_json(json.loads(result.decode()))

            # hit 되지 않으므로 인식 요청을 수행
            if not self._check_storage(self.s3_file_key):
                # 인식 요청 수행 전 인식 할 파일이 있는지 확인
                self._upload_to_storage(self.filename, self.s3_file_key)

            # 음성 인식 수행
            self._request_to_process(data_key, lang, vendor)
            return Transcription.from_json(json.loads(self._wait_for_response(data_key).decode()))


class TranscriptionBroker:
    def __init__(self, builder: RedisBuilder, downloader: BaseDownloader):
        self.__builder = builder
        self.__downloader = downloader

    def with_file(self, filename: str, unique_key: str) -> TranscriptionContext:
        unique_key2 = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        return TranscriptionContext(self.__builder, self.__downloader, filename, unique_key, unique_key2)
