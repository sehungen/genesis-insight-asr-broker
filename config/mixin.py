import os

import yaml
import orjson

from pydantic import BaseModel


class YamlMixin(BaseModel):
    @classmethod
    def load_from_yml(cls, filename: str):
        with open(filename, 'r') as file:
            yml = yaml.full_load(file)
            return cls(**yml)


class EnvVarMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        env_prefix = self.__class__.__name__[:-6].upper()
        for field_name, field in self.__fields__.items():
            env_key = f'{env_prefix}_{field_name.upper()}'
            env = os.environ.get(env_key)
            if env:
                field_type = field.outer_type_
                value = env if field_type == str else orjson.loads(env)
                setattr(self, field_name, value)


class KwargsMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def kwargs(self):
        return self.__dict__
