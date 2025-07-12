from .base import FlaiService
from flai_sdk.models.flow_templates import CreateLocalFlow
import json


class FlaiFlowTemplates(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}/flow-templates'

    def get_flow_templates(self):
        return self.client.get(f'{self.service_url}')

    def convert_template_to_local_flow(self, flow_template_id, create_local_flow_status: CreateLocalFlow):
        return json.loads(self.client.post(f'{self.service_url}/{flow_template_id}/to-local',
                                           json=create_local_flow_status.dict()))
