from pathlib import Path

from zinolib.config.toml import parse_toml_config
from .models import HowitzConfig, DevHowitzConfig


class Config:

    @classmethod
    def get_class(cls, devmode=False):
        classobj = DevHowitzConfig if devmode else HowitzConfig
        return type("Config", (classobj, cls), {})

    @classmethod
    def from_args(cls, args):
        "Assumes argparse-style args namespace object"
        config_dict = {
            'port': args.port,
            'listen': args.listen,
            'storage': args.storage,
        }
        Config = cls.get_class(args.devmode)
        return Config(**config_dict)

    @classmethod
    def from_toml(cls,filename=None):
        """Format:

        [howitz]
        listen = "127.0.0.1"
        port = 9000
        storage = "./howitz.sqlite3"
        devmode = false
        """
        if not filename:
            filename = 'howitz.toml'
        config_dict = parse_toml_config(filename)
        howitz_dict = config_dict['howitz']
        Config = cls.get_class(howitz_dict.get("devmode"))
        return Config(**howitz_dict)

    def update_from_args(self, args):
        """
        Assumes argparse-style args namespace object

        arg-names not found in the config-object are ignored.
        """
        for arg in vars(args):
            value = getattr(args, arg, None)
            if value and arg in vars(self):
                setattr(self, arg, value)
