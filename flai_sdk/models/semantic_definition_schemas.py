from flai_sdk.models.base import BaseModel


class GenericSemanticDefinitionSchema(BaseModel):

    def __init__(self, labels: list, dataset_type: str= None):
        self.labels = labels
        self.dataset_type = dataset_type
