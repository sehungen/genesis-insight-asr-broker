from redis import StrictRedis

from config import MainConfig
from downloader import AwsS3Downloader
from transcribers import AwsTranscriber, ClovaNestTranscriber
from transcribers.enums import Vendor

from runner import ParallelExecutor, TranscriptionRequestRunner

import click
import logging


@click.command()
@click.option('-c', '--config_path', default='config/config-local.yml', help='config yaml file path', show_default=True)
def main(config_path: str):
    config = MainConfig.load_from_yml(config_path)
    config.logger.setup()
    redis = StrictRedis(**config.redis.kwargs)
    downloader = AwsS3Downloader(config.aws.bucket, **config.aws.session_param)
    executor = ParallelExecutor(**config.executor.kwargs)

    transcribers = {
        Vendor.AWS: (False, AwsTranscriber(**config.aws.kwargs)),
        Vendor.ClovaNest: (True, ClovaNestTranscriber(**{**config.clova_nest.kwargs, **config.aws.kwargs}))
    }

    logging.info('Starting Insight-ASR broker')
    runner = TranscriptionRequestRunner(redis, transcribers, executor, downloader, config.cache.dirpath)
    runner.poll()


if __name__ == '__main__':
    main()
