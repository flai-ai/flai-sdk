from flai_sdk.models.base import BaseModel


class FlowNodeExecutionFile(BaseModel):

    def __init__(self, flow_node_execution_id: str, filename: str, file_hash: str, storage_type: str = '', dataset_id: str = '', status: str = '', message: str = '', billing: dict = {}):
        self.flow_node_execution_id = flow_node_execution_id
        self.filename = filename
        self.storage_type = storage_type
        self.dataset_id = dataset_id
        self.file_hash = file_hash
        self.status = status
        self.message = message
        self.billing = billing

        
class CheckProcessingFlowNodeExecutionFile(BaseModel):

    def __init__(self, flow_node_execution_id: str, filename: str, file_hash: str = None, storage_type: str = None, dataset_id: str = None, status: str = None, message: str = None, task_name: str = None, billing: dict = {}):
        self.flow_node_execution_id = flow_node_execution_id
        self.filename = filename
        self.storage_type = storage_type
        self.dataset_id = dataset_id
        self.file_hash = file_hash
        self.status = status
        self.message = message
        self.task_name = task_name
        self.billing = billing


class FlowNodeExecution(BaseModel):

    def __init__(self, status: str, message: str = None, task_id: str = None, started_at: str = None, finished_at: str = None):
        self.status = status
        self.message = message
        self.task_id = task_id
        self.started_at = started_at
        self.finished_at = finished_at


class FlowNodeDistributedExecution(BaseModel):

    def __init__(self, flow_node_execution_id: str, execution_time: float, runtime_environment: str, distributed_queue: str = ''):
        self.flow_node_execution_id = flow_node_execution_id
        self.execution_time = execution_time
        self.runtime_environment = runtime_environment
        self.distributed_queue = distributed_queue
