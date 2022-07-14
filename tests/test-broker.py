from typing import Callable

from redis import StrictRedis

from client import RedisBuilder, TranscriptionBroker
from config import MainConfig
from downloader import AwsS3Downloader

from transcribers import Lang, Vendor

import redis_lock
import click


@click.command()
@click.option('-c', '--config_path', default='config/config-local.yml', help='config yaml file path', show_default=True)
def main(config_path: str):
    config = MainConfig.load_from_yml(config_path)
    redis = StrictRedis(**config.redis.kwargs)
    downloader = AwsS3Downloader(config.aws.bucket, **config.aws.session_param)

    filename = r'tests/test-file.wav'
    unique_key = 'broker-test'

    class MyRedisBuilder(RedisBuilder):
        @property
        def redis_lock(self) -> Callable:
            return redis_lock.Lock

        @property
        def redis(self) -> Callable:
            return lambda: redis

    broker = TranscriptionBroker(MyRedisBuilder(), downloader)

    with broker.with_file(filename, unique_key) as context:
        trans_cn = context.transcribe(vendor=Vendor.ClovaNest)
        print(f'Test (ClovaNest): {trans_cn.transcripts}')
        trans_aw = context.transcribe(vendor=Vendor.AWS)
        print(f'Test (AWS): {trans_aw.transcripts}')


if __name__ == '__main__':
    main()

