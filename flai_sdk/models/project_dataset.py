from flai_sdk.models.base import BaseModel


class ProjectDataset(BaseModel):

    def __init__(self, project_id: str = '', dataset_id: str = ''):
        self.project_id = project_id
        self.dataset_id = dataset_id
