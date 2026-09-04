from abc import ABCMeta
from typing import Optional

import flai_sdk.config
from flai_sdk.api import client


PUBLIC_ENDPOINT = 'public'
API_ENDPOINT    = 'api/v1'


class FlaiPublicService(metaclass=ABCMeta):

    endpoint = PUBLIC_ENDPOINT

    def __init__(self, config=None, access_token: str = None, flai_host: str = None, api_url: str = None):
        self.config = config or flai_sdk.config.Config()
        self.config.apply_overrides(access_token=access_token, flai_host=flai_host, api_url=api_url)
        self.client = client.Client(config=self.config)
        self.decorators_string = '?decorators='

        self.base_url = f'{self.config.flai_host.rstrip("/")}/{self.endpoint}'
        self.active_org_id = self._resolve_org_id()
        self.service_url = self._get_service_url(self.base_url, self.active_org_id)

    def _resolve_org_id(self) -> Optional[str]:
        return None

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        """Service specific url"""


class FlaiNoAuthService(FlaiPublicService):

    endpoint = API_ENDPOINT


class FlaiService(FlaiPublicService):

    endpoint = API_ENDPOINT

    def _resolve_org_id(self) -> str:
        return self.client.get(f'{self.base_url}/oauth/me')['active_organization_id']
