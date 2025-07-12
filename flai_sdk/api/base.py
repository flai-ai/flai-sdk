from abc import ABCMeta, abstractmethod

import flai_sdk.config
from flai_sdk.api import client


class FlaiService(metaclass=ABCMeta):

    def __init__(self):
        self.config = flai_sdk.config.Config()
        self.client = client.Client(config=self.config)

        self.base_url = f'{self.config.flai_host.rstrip("/")}/api/v1'

        self.active_org_id = self.client.get(f'{self.base_url}/oauth/me')['active_organization_id']

        self.service_url = self._get_service_url(self.base_url, self.active_org_id)

        self.decorators_string = '?decorators='

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        """Service pecific url"""
