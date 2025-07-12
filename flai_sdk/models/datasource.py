from flai_sdk.models.base import BaseModel


class Datasource(BaseModel):

    def __init__(self, credentials: dict = None, datasource_type: str = 's3', datasource_address: str = None,
                 path: str = None):
        self.path = path
        self.datasource_address = datasource_address
        self.datasource_type = datasource_type
        self.credentials = credentials
