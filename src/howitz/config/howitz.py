from pathlib import Path

from zinolib.config.toml import parse_toml_config
from .models import HowitzConfig, DevHowitzConfig


class Config:

    @classmethod
    def get_class(cls, devmode=False):
        classobj = DevHowitzConfig if devmode else HowitzConfig
        return type("Config", (classobj, cls), {})

    @classmethod
    def from_dict(cls, config_dict):
        howitz_dict = config_dict.get('howitz', {})
        devmode = howitz_dict.get("devmode", True)
        Config = cls.get_class(devmode)
        return Config(**howitz_dict)

    @classmethod
    def from_toml(cls, filename=None):
        """Format:

        [howitz]
        storage = "./howitz.sqlite3"
        devmode = false
        """
        if not filename:
            filename = 'howitz.toml'
        config_dict = parse_toml_config(filename)
        return cls.from_dict(config_dict)


def make_howitz_config(config_dict, prefix='HOWITZ'):
    howitz_config_dict = {}
    if prefix and not prefix.endswith('_'):
        prefix = f"{prefix}_"
    for k, v in config_dict.copy().items():
        if not k.startswith(prefix):
            continue
        k = k[len(prefix):]
        k = k.lower()
        howitz_config_dict[k] = v
    return howitz_config_dict
