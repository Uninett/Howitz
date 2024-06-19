from typing import Literal

from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress

from howitz.config.defaults import DEFAULT_TIMEZONE, DEFAULT_STORAGE
from howitz.endpoints import EventSort


class ServerConfig(BaseModel):
    listen: IPvAnyAddress
    port: int


class DevServerConfig(ServerConfig):
    listen: IPvAnyAddress = "127.0.0.1"
    port: int = 9000


class StorageConfig(BaseModel):
    storage: str


class DevStorageConfig(StorageConfig):
    storage: str = DEFAULT_STORAGE


class HowitzConfig(ServerConfig, StorageConfig):
    devmode: bool = Literal[False]
    refresh_interval: int = 5
    timezone: str = DEFAULT_TIMEZONE
    sort_by: str = str(EventSort.DEFAULT)


class DevHowitzConfig(DevServerConfig, DevStorageConfig):
    devmode: bool = Literal[True]
    refresh_interval: int = 5
    timezone: str = DEFAULT_TIMEZONE
    sort_by: str = str(EventSort.DEFAULT)
