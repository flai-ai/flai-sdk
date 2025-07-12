import json
from pathlib import Path
import os


class Config:

    CONFIG_PARAMS = [
        "flai_cli_client_id",
    ]

    config_filepath = Path.home() / Path('.flai_client')

    def __init__(self):
        self.flai_cli_client_id: str = ""
        self.load()

    def set(self, **kwargs):
        for key, value in kwargs.items():
            if key not in self.CONFIG_PARAMS:
                continue
            setattr(self, key, value)
        self.save()

    def load(self) -> bool:
        """
        Load configuration file

        :return:
        """
        if self.config_filepath.is_file():
            with open(self.config_filepath, "r") as cfg_file:
                config_dict = json.load(cfg_file)

            for param, value in config_dict.items():
                if param in self.CONFIG_PARAMS:
                    setattr(self, param, value)
        else:
            for param in self.CONFIG_PARAMS:
                setattr(self, param, os.getenv(param.upper(), ''))

        return True

    def save(self) -> bool:
        """
        Save configuration file

        :return:
        """
        config_dict = {param: getattr(self, param) for param in self.CONFIG_PARAMS}
        with open(self.config_filepath, "w") as cfg_file:
            json.dump(config_dict, cfg_file, indent=2)

        return True
