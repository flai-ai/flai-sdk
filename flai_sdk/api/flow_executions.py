from .base import FlaiService
from flai_sdk.models.flow_executions import FlowNodeExecutionFile, FlowNodeExecution, CheckProcessingFlowNodeExecutionFile, FlowNodeDistributedExecution
import json


class FlaiFlowExecutions(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/organization/{active_org_id}"

    def post_flow_node_execution_file(self, cli_execution_progress: FlowNodeExecutionFile) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/flow-node-execution-files',
                                           json=cli_execution_progress.dict()))

    def post_check_file_processing(self, file_execution_progress: CheckProcessingFlowNodeExecutionFile) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/flow-node-execution-files/check-processing',
                                           json=file_execution_progress.dict()))

    def update_flow_node_execution(self, flow_node_execution_id, flow_node_execution_status: FlowNodeExecution) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/flow-node-executions/{flow_node_execution_id}',
                                           json=flow_node_execution_status.dict()))

    def post_distributed_execution(self, file_execution_progress: FlowNodeDistributedExecution) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/flow-node-distributed-executions',
                                           json=file_execution_progress.dict()))


