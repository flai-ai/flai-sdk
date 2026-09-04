from .base import FlaiService
from flai_sdk.models.flows import LocalFlowExecutionsList

class FlaiFlows(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}'

    def get_local_flow_executions(self, increase_flow_list: LocalFlowExecutionsList = LocalFlowExecutionsList()):
        return self.client.get(f'{self.service_url}/flow-executions-local', json=increase_flow_list.dict())

    def get_flow_executions(self):
        return self.client.get(f'{self.service_url}/flow-executions')

    def get_flow_execution(self, flow_execution_id):
        return self.client.get(f'{self.service_url}/flow-executions/{flow_execution_id}')

    def get_flow(self, flow_id: str, get_nodes: bool = False, get_edges: bool = False) -> dict:

        decorators = []
        if get_nodes:
            decorators.append('flow_nodes')
        if get_edges:
            decorators.append('flow_edges')

        if len(decorators) > 0:
            decorators = f'{self.decorators_string}{",".join(decorators)}'
        else:
            decorators = ''

        return self.client.get(f'{self.service_url}/flows/{flow_id}{decorators}')

    def create_flow(self, payload: dict) -> str:
        """Create a flow from a payload dict and return the new flow id.

        `payload` follows the flai-be create contract:
            {
              "title": str,                         # required
              "description": str | None,
              "project_id": str | None,
              "flow_nodes": [                        # required, >= 1
                {"id", "flow_node_definition_id", "flow_node_key",
                 "options": {...}, "position": {...}}
              ],
              "flow_edges": [
                {"from_flow_node_id", "to_flow_node_id",
                 "from_connector", "to_connector", "to_connector_order"}
              ]
            }

        The flow is created in the token's active organization. See the flai-cortex
        `flow_catalog` package for how to build the payload from node definitions.
        """
        response = self.client.parse_response_from_text(
            self.client.post(f'{self.service_url}/flows', json=payload)
        )
        if isinstance(response, dict):
            return response.get('id') or (response.get('data') or {}).get('id')
        return response
