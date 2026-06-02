from flai_sdk.models.base import BaseModel


class FlaiPipelineRunnerNodeCompleted(BaseModel):

    def __init__(
        self,
        node_title: str = None,
        node_command_name: str = None,
        node_id: str = None,
        node_response: dict = None,
        flow_id: str = None,
        flow_execution_id: str = None,
        node_settings: dict = None,
        status: str = None,
        started_at: str = None,
        finished_at: str = None,
        billing: dict = None,
        point_worker_command_id: str = None,
        finished: str = None,
        runtime_seconds: str = None,
        msg: str = None,
        requeue: str = None,
    ):
        self.node_title = node_title
        self.node_command_name = node_command_name
        self.node_id = node_id
        self.node_response = node_response
        self.flow_id = flow_id
        self.flow_execution_id = flow_execution_id
        self.node_settings = node_settings
        self.status = status
        self.started_at = started_at
        self.finished_at = finished_at
        self.billing = billing
        self.point_worker_command_id = point_worker_command_id
        self.finished = finished
        self.runtime_seconds = runtime_seconds
        self.msg = msg
        self.requeue = requeue
