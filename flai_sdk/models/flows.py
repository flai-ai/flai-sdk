from flai_sdk.models.base import BaseModel


class LocalFlowExecutionsList(BaseModel):

    def __init__(self, flow_id: str = '', count: int = 30):
        self.flow_id = flow_id 
        self.count   = count