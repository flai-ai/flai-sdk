from .base import FlaiService
from flai_sdk.models.cli_executions import CliExecution, CliExecutionPartialUpdate
import json


class FlaiCliExecutions(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/organization/{active_org_id}/cli-clients"

    def post_cli_execution(self, client_id: str, cli_execution: CliExecution) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/{client_id}/cli-executions', json=cli_execution.dict()))

    def patch_cli_execution(self, client_id: str, cli_execution_id: str, cli_execution: CliExecution) -> dict:
        return json.loads(self.client.put(f'{self.service_url}/{client_id}/cli-executions/{cli_execution_id}',
                                          json=cli_execution.dict()))

    def patch_cli_execution_partial_update(self, client_id: str, cli_execution_id: str, cli_execution_partial_update: CliExecutionPartialUpdate) -> dict:
        return json.loads(self.client.put(f'{self.service_url}/{client_id}/cli-executions-partial-update/{cli_execution_id}',
                                          json=cli_execution_partial_update.dict()))
