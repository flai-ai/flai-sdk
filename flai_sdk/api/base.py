from abc import ABCMeta

import flai_sdk.config
from flai_sdk.api import client


PUBLIC_ENDPOINT = 'public'
API_ENDPOINT    = 'api/v1'


class FlaiPublicService(metaclass=ABCMeta):

    def __init__(self):
        self.config = flai_sdk.config.Config()
        self.client = client.Client(config=self.config)

        self.base_url = f'{self.config.flai_host.rstrip("/")}/{PUBLIC_ENDPOINT}'
        self.service_url = self._get_service_url(self.base_url)
        self.decorators_string = '?decorators='

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        """Service specific url"""


class FlaiNoAuthService(FlaiPublicService):
    
    def __init__(self):
        super().__init__()
        self.base_url = f'{self.config.flai_host.rstrip("/")}/{API_ENDPOINT}'
        self.service_url = self._get_service_url(self.base_url, None)


class FlaiService(FlaiPublicService):

    def __init__(self):
        super().__init__()
        self.base_url = f'{self.config.flai_host.rstrip("/")}/{API_ENDPOINT}'
        self.active_org_id = self.client.get(f'{self.base_url}/oauth/me')['active_organization_id']
        
        self.service_url = self._get_service_url(self.base_url, self.active_org_id)
