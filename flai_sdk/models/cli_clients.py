from flai_sdk.models.base import BaseModel


class CliClient(BaseModel):

    def __init__(self, fingerprint: str = '', metadata: str = '', mac_address: str = '', version: str = '', os_info: str = ''):
        self.fingerprint = fingerprint
        self.mac_address = mac_address
        self.metadata = metadata
        self.version = version
        self.os_info = os_info
