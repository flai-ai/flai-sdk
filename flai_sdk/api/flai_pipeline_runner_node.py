from .base import FlaiService
from flai_sdk.models.flai_pipeline_runner_node import FlaiPipelineRunnerNodeCompleted
import json


class FlaiPipelineRunnerNode(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/organization/{active_org_id}"

    def complete(self, payload: FlaiPipelineRunnerNodeCompleted) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/pipeline-runner-flow-node/complete',
                                           json=payload.dict()))

    def fail(self, payload: FlaiPipelineRunnerNodeCompleted) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/pipeline-runner-flow-node/fail',
                                           json=payload.dict()))
