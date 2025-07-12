from flai_sdk.models.base import BaseModel


class CreateLocalFlow(BaseModel):

    def __init__(self,
                 flow_title: str = None,
                 project_id: str = None,
                 flow_node_options: list = None,
                 ):
        self.flow_title = flow_title
        self.project_id = project_id
        self.flow_node_options = flow_node_options
