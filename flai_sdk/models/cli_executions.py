from flai_sdk.models.base import BaseModel


class CliExecution(BaseModel):

    def __init__(self, flow_id: str, status: str = '', finished_at: str = '', node_completed_payload: dict = {}, cli_license_id: str = ''):
        self.finished_at = finished_at
        self.status = status
        self.flow_id = flow_id
        self.node_completed_payload = node_completed_payload
        self.cli_license_id = cli_license_id


class CliExecutionPartialUpdate(BaseModel):
    def __init__(self, flow_id: str, partial_update_payload: dict = {}):
        self.flow_id = flow_id
        self.partial_update_payload = partial_update_payload
