from flai_sdk.models.base import BaseModel


class Project(BaseModel):

    def __init__(self, name: str = '', description: str = '', status: str =''):
        self.name = name
        self.description = description
