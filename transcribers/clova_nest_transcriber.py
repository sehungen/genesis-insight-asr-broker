from .base_transcriber import BaseTranscriber
from .enums import Lang, Vendor
from .transcription import Transcription, TranscriptionWord

from smart_open import open

import logging
import json

import boto3
import requests


logger = logging.getLogger(__name__)


class ClovaNestTranscriber(BaseTranscriber):
    def __init__(self, invoke_url: str, secret_key: str, callback: str, access_key: str, secret_access_key: str, region: str, bucket: str):
        self.__invoke_url = invoke_url
        self.__secret_key = secret_key
        self.__aws_bucket = bucket
        self.__aws_client = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key, region_name=region)
        self.__callback_url = callback

    def req_upload(self, file, completion, callback=None, userdata=None, forbiddens=None, boostings=None, wordAlignment=True, fullText=True, diarization=None):
        request_body = {
            'language': 'ko-KR',
            'completion': completion,
            'callback': callback,
            'userdata': userdata,
            'wordAlignment': wordAlignment,
            'fullText': fullText,
            'forbiddens': forbiddens,
            'boostings': boostings,
            'diarization': diarization,
        }

        headers = {
            'Accept': 'application/json;UTF-8',
            'X-CLOVASPEECH-API-KEY': self.__secret_key
        }

        files = {
            'media': file,
            'params': (None, json.dumps(request_body, ensure_ascii=False).encode(), 'application/json')
        }

        response = requests.post(headers=headers, url=self.__invoke_url + '/recognizer/upload', files=files)
        return response

    def transcribe(self, src: str, lang: Lang):
        uri = f's3://{self.__aws_bucket}/{src}'
        try:
            logging.info(f'Started to transcribe. [ClovaNest] Src={src}')
            with open(uri, 'rb', transport_params={'client': self.__aws_client}) as f:
                kwargs = {'completion': 'sync'}
                use_webhook = not not self.__callback_url
                if use_webhook:
                    kwargs.update({'completion': 'async', 'callback': self.__callback_url})

                result = self.req_upload(f, **kwargs).json()

                # 웹훅을 사용한다면, 토큰을 반환
                if use_webhook:
                    token = result.get('token')
                    if token:
                        logging.info(f'Transcriber does not wait for response [ClovaNest] Src={src}, Token={token}')
                        return token
                    logging.error(f'Failed to transcribe in async mode. [ClovaNest] Src={src}')
                    return None

                # 동기 통신을 사용한다면 반환값을 그대로 사용한다.
                words = []
                for segment in result.get('segments', []):
                    for word in segment.get('words', []):
                        words.append(TranscriptionWord(word[2], word[0] / 1000, word[1] / 1000))
                transcription = Transcription([result.get('text')], [result.get('confidence')], words, Vendor.ClovaNest.value)
                logging.info(f'Transcribing is completed [ClovaNest] Src={src}')
                return transcription
        except Exception as e:
            logging.error(f'Failed to transcribe. [ClovaNest] Src={src}')
            return None
