from .base import FlaiService
from flai_sdk.models.datasets import Dataset, LocalDataset
from flai_sdk.models.datasource import Datasource
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

    def get_dataset(self, dataset_id: str):
        return self.client.get(f"{self.service_url}/{dataset_id}")

    def post_datasets(self, dataset: Dataset) -> dict:
        if dataset.import_datasource is None:
            raise Exception('Import datasource has to be set if creating dataset. If you would like to also upload'
                            ' dataset please use upload_and_post_datasets method')

        return self.client.post(self.service_url, dataset.dict())

    def post_local_datasets(self, local_dataset: LocalDataset) -> dict:

        return json.loads(self.client.post(
            f"{self.service_url}/local",
            local_dataset.dict()
        ))

    def download_datasets(self, dataset_id) -> dict:
        return json.loads(self.client.post(f"{self.service_url}/{dataset_id}/download"))

    def upload_and_post_datasets(self, dataset: Dataset, path: Path) -> dict:
        flai_upload = upload.FlaiUpload()
        upload_response = flai_upload.upload_file(path, dataset.dataset_type_key)
        dataset.import_datasource = Datasource({}, datasource_type='upload_storage_tmp', datasource_address="/",
                                               path=upload_response['end_filename'])

        return json.loads(self.client.post(self.service_url, json=dataset.dict()))

    def upload_precomputed_copc(self, dataset: Dataset, path: Path,
                               dataset_stats: dict = None, file_stats: list = None) -> dict:
        """Upload a pre-computed COPC dataset, skipping server-side preprocessing.

        The path should point to a directory or zip containing:
        - One or more .copc.laz files (point cloud data)
        - overview.copc.laz (reduced-density overview for the viewer)

        Args:
            dataset: Dataset metadata
            path: Path to directory or zip file containing pre-computed COPC files
            dataset_stats: Optional dataset-level stats dict with keys:
                point_count, point_density, area, classification_hist,
                intensity_hist, num_returns_hist, return_num_hist
            file_stats: Optional list of per-file stats dicts with keys:
                file_name, folder, classification_hist, intensity_hist,
                num_returns_hist, return_num_hist
        """
        dataset.skip_preprocessing = True
        result = self.upload_and_post_datasets(dataset, path)

        if dataset_stats is not None or file_stats is not None:
            dataset_id = result['id']
            self.add_precomputed_stats(dataset_id, dataset_stats or {}, file_stats or [])

        return result

    def add_precomputed_stats(self, dataset_id: str, dataset_stats: dict, file_stats: list) -> dict:
        """Push both dataset-level and per-file stats for a pre-computed COPC dataset."""
        return json.loads(
            self.client.put(
                f"{self.service_url}/{dataset_id}/pointcloud-precomputed-stats",
                json={
                    'dataset_stats': dataset_stats,
                    'file_stats': file_stats,
                },
            )
        )

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

    def get_dataset_images(self, dataset_id: str) -> dict:
        return self.client.get(f"{self.service_url}/{dataset_id}/images")
