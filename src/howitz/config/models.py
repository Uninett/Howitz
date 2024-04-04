from typing import Literal

from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress

from howitz.config.defaults import DEFAULT_TIMEZONE, DEFAULT_STORAGE
from howitz.endpoints import EventSorting


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
    poll_interval: int = 60
    timezone: str = DEFAULT_TIMEZONE
    sort_by: str = EventSorting.DEFAULT


class DevHowitzConfig(DevServerConfig, DevStorageConfig):
    devmode: bool = Literal[True]
    poll_interval: int = 30
    timezone: str = DEFAULT_TIMEZONE
    sort_by: str = EventSorting.DEFAULT
