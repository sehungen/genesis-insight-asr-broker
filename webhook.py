import logging

from fastapi import FastAPI
from starlette.responses import Response
from pydantic import BaseModel
from redis import StrictRedis

import uvicorn
import click

from typing import List

from config import WebHookMainConfig

from transcribers import Transcription, TranscriptionWord, Vendor


class ClovaNestParams(BaseModel):
    service: str
    domain: str
    completion: str
    diarization: dict
    boostings: dict
    forbiddens: str
    wordAlignment: bool
    fullText: bool
    priority: int
    userdata: dict


class ClovaNestResult(BaseModel):
    result: str
    message: str
    token: str
    version: str
    params: ClovaNestParams
    progress: int
    segments: List[dict]
    text: str
    confidence: float
    speakers: List[dict]


@click.command()
@click.option('-c', '--config_path', default='config/config-local.yml', help='config yaml file path', show_default=True)
def main(config_path: str):
    config = WebHookMainConfig.load_from_yml(config_path)
    config.logger.setup()
    redis = StrictRedis(**config.redis.kwargs)

    app = FastAPI()

    @app.post('/clovanest/webhook')
    async def clovanest_webhook(result: ClovaNestResult):
        logging.info(f'WebHook is delivered from ClovaNest. result={result.result}, token={result.token}')
        webhook_key = f'transcriber-webhook:{result.token}'
        data_key = redis.get(webhook_key)
        if not data_key:
            # 웹훅키에서 데이터키를 찾을 수 없다 - 무시
            logging.info(f'Cannot found data key from ClovaNest token. token={result.token}')
        else:
            # 웹훅키에서 데이터키를 찾았다 - 데이터키로 음성인식 결과 기록
            logging.info(f'Data key is found from ClovaNest token. data_key={data_key.decode()}, token={result.token}')
            words = []
            for segment in result.segments:
                for word in segment.get('words', []):
                    words.append(TranscriptionWord(word[2], word[0] / 1000, word[1] / 1000))
            transcription = Transcription([result.text], [result.confidence], words, Vendor.ClovaNest.value)
            redis.set(data_key, transcription.tojson())

        # 웹훅키는 지운다
        redis.delete(webhook_key)
        return Response()

    @app.get('/')
    async def root():
        return Response(':)')

    uvicorn.run(app, **config.webhook.kwargs)


if __name__ == '__main__':
    main()
