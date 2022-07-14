from .mixin import YamlMixin, EnvVarMixin, KwargsMixin
from logging.handlers import RotatingFileHandler

import os
import logging


class AwsConfig(EnvVarMixin, YamlMixin, KwargsMixin):
    access_key: str
    secret_access_key: str
    bucket: str
    region: str

    @property
    def session_param(self):
        return {
            'aws_access_key_id': self.access_key,
            'aws_secret_access_key': self.secret_access_key,
            'region_name': self.region,
        }


class ClovaNestConfig(EnvVarMixin, YamlMixin, KwargsMixin):
    invoke_url: str
    secret_key: str
    callback: str


class RedisConfig(EnvVarMixin, YamlMixin, KwargsMixin):
    host: str
    port: int
    db: int


class LoggerConfig(EnvVarMixin, YamlMixin):
    filename: str = 'logs/asr-broker.log'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    level: str = logging.DEBUG
    sql_level: str = logging.WARN

    def setup(self):
        log_dir = os.path.dirname(self.filename)
        os.makedirs(log_dir, exist_ok=True)
        handlers = [
            RotatingFileHandler(self.filename, encoding='utf-8', maxBytes=100 * 1024 * 1024),
            logging.StreamHandler()
        ]
        logging.basicConfig(format=self.format, level=self.level, handlers=handlers)


class ExecutorConfig(EnvVarMixin, YamlMixin, KwargsMixin):
    max_request: int


class CacheConfig(EnvVarMixin, YamlMixin):
    dirpath: str


class MainConfig(EnvVarMixin, YamlMixin):
    aws: AwsConfig
    clova_nest: ClovaNestConfig
    redis: RedisConfig
    cache: CacheConfig
    executor: ExecutorConfig
    logger: LoggerConfig


class WebHookConfig(EnvVarMixin, YamlMixin, KwargsMixin):
    host: str
    port: int


class WebHookMainConfig(EnvVarMixin, YamlMixin):
    webhook: WebHookConfig
    redis: RedisConfig
    logger: LoggerConfig
