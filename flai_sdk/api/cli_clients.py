from .base import FlaiService
from flai_sdk.models.cli_clients import CliClient
import json


class FlaiCliClient(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/organization/{active_org_id}/cli-clients"

    def get_cli_clients(self):
        return self.client.get(self.service_url)

    def validate_cli_client(self, cli_client_id: str) -> dict:
        return self.client.get(f'{self.service_url}/{cli_client_id}/validate')

    def activity_ping_cli_client(self, cli_client_id: str) -> dict:
        return self.client.get(f'{self.service_url}/{cli_client_id}/ping')

    def inactivate_cli_client(self, cli_client_id: str) -> dict:
        return self.client.get(f'{self.service_url}/{cli_client_id}/inactive')

    def check_latest_version_cli_client(self, cli_client_id: str, version: str) -> dict:
        return self.client.get(f'{self.service_url}/{cli_client_id}/check_version',
                               json={'version': version})

    def get_cli_client(self, cli_client_id: str, fingerprint: str):
        return self.client.get(f'{self.service_url}/{cli_client_id}',
                               json={'fingerprint': fingerprint})

    def get_cli_client_by_host_id(self, fingerprint: str):
        return self.client.get(f'{self.service_url}/check_fingerprint/{fingerprint}')

    def post_cli_client(self, cli_client: CliClient) -> dict:
        return json.loads(self.client.post(self.service_url, json=cli_client.dict()))

