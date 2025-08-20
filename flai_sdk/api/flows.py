from .base import FlaiService


class FlaiFlows(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}'

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
