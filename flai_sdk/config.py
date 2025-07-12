import json
from typing import Any, Dict, Iterable, List, Optional, Union
from pathlib import Path
import os

ConfigDict = Dict[str, Union[str, int, float]]


class Config:
    CONFIG_PARAMS = [
        "flai_access_token",
        "flai_host",
        "flai_licence_key",
        "flai_data",
    ]

    config_filepath = Path.home() / Path('.flai')

    def __init__(self):
        self.flai_access_token: str = ""
        self.flai_host: str = "https://api.flai.ai"
        self.flai_licence_key: str = ""
        self.flai_data: dict = {}
        self.load()

    def info(self):
        for param in self.CONFIG_PARAMS:
            print(f'{param}: {getattr(self, param)}')

    def get_web_app_url(self):
        return self.flai_host.replace('api.', 'app.')

    def set(self, **kwargs):
        for key, value in kwargs.items():
            if key not in self.CONFIG_PARAMS:
                continue
            setattr(self, key, value)
        self.save()

    def get_params(self) -> List[str]:
        return list(self.CONFIG_PARAMS)

    def load(self):
        if self.config_filepath.is_file():
            with open(self.config_filepath, "r") as cfg_file:
                config_dict = json.load(cfg_file)

            for param, value in config_dict.items():
                if param in self.CONFIG_PARAMS:
                    setattr(self, param, value)
        else:
            # this is probably problematic for saving
            for param in self.CONFIG_PARAMS:
                setattr(self, param, os.getenv(param.upper(), ''))

    def save(self) -> None:
        """
        Save configuration file
        :return:
        """
        config_dict = {param: getattr(self, param) for param in self.CONFIG_PARAMS}
        with open(self.config_filepath, "w") as cfg_file:
            json.dump(config_dict, cfg_file, indent=2)
