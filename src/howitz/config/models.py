from typing import Literal

from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress


DEFAULT_STORAGE = "./howitz.sqlite3"


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


class DevHowitzConfig(DevServerConfig, DevStorageConfig):
    devmode: bool = Literal[True]
