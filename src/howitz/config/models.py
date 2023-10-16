from typing import Literal

from pydantic import BaseModel
from pydantic.networks import IPvAnyAddress


class ServerConfig(BaseModel):
    listen: IPvAnyAddress
    port: int
    devmode: bool = Literal[False]


class DevServerConfig(ServerConfig):
    listen: IPvAnyAddress = "127.0.0.1"
    port: int = 9000
    devmode: bool = Literal[True]
