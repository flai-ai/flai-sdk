from flai_sdk.models.base import BaseModel


class PointcloudStats(BaseModel):

    def __init__(self,
                 file_name: str,
                 folder: str = None,
                 intensity_hist: list = None,
                 num_returns_hist: list = None,
                 return_num_hist: list = None,
                 classification_hist: list = None
                 ):

        self.file_name = file_name
        self.folder = folder
        self.intensity_hist = intensity_hist
        self.num_returns_hist = num_returns_hist
        self.return_num_hist = return_num_hist
        self.classification_hist = classification_hist
