from pathlib import Path

from .models import HowitzConfig, DevHowitzConfig


class Config:

    @staticmethod
    def from_args(args):
        "Assumes argparse-style args namespace object"
        config_dict = {
            'port': args.port,
            'listen': args.listen,
            'storage': args.storage,
        }
        cls = DevHowitzConfig if args.devmode else HowitzConfig
        return cls(**config_dict)

    def update_from_args(self, args):
        """
        Assumes argparse-style args namespace object

        arg-names not found in the config-object are ignored.
        """
        for arg in vars(args):
            value = getattr(args, arg, None)
            if arg in vars(self):
                setattr(self, arg, value)
