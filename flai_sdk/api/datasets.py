from .base import FlaiService
from flai_sdk.models.datasets import Dataset, Datasource
from flai_sdk.api import upload
from flai_sdk.models.pointclouds import PointcloudStats
from pathlib import Path
import json


class FlaiDataset(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/organization/{active_org_id}/datasets"

    def get_datasets(self):
        return self.client.get(self.service_url)

    def post_datasets(self, dataset: Dataset) -> dict:
        if dataset.import_datasource is None:
            raise Exception('Import datasource has to be set if creating dataset. If you would like to also upload'
                            ' dataset please use upload_and_post_datasets method')

        return self.client.post(self.service_url, dataset.dict())

    def download_datasets(self, dataset_id) -> dict:
        return json.loads(self.client.post(f"{self.service_url}/{dataset_id}/download"))

    def upload_and_post_datasets(self, dataset: Dataset, path: Path) -> dict:
        flai_upload = upload.FlaiUpload()
        upload_response = flai_upload.upload_file(path, dataset.dataset_type_key)
        dataset.import_datasource = Datasource({}, datasource_type='upload_storage_tmp', datasource_address="/",
                                               path=upload_response['end_filename'])

        return json.loads(self.client.post(self.service_url, json=dataset.dict()))

    def create_vector_without_file_datasets(self, dataset: Dataset) -> dict:
        if dataset.vector_dataset is None:
            raise Exception('Vector dataset structure has to be set if creating dataset without files.')

        return json.loads(self.client.post(self.service_url, json=dataset.dict()))

    def add_stats_to_pointcloud_entry(self, dataset_id: str, pointcloud_stats: PointcloudStats) -> dict:
        return json.loads(
            self.client.put(
                f"{self.service_url}/{dataset_id}/pointcloud-add-stats",
                json=pointcloud_stats.dict(),
            )
        )
