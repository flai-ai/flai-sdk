from .base import FlaiService
from flai_sdk.models.datasets import Dataset, LocalDataset
from flai_sdk.models.datasource import Datasource
from flai_sdk.api import upload
from flai_sdk.models.pointclouds import PointcloudStats
from pathlib import Path
from typing import List, Union
import json
import uuid


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

    def upload_and_post_datasets(self, dataset: Dataset, path: Path, progress_callback=None) -> dict:
        flai_upload = upload.FlaiUpload(config=self.config)
        upload_response = flai_upload.upload_file(path, dataset.dataset_type_key,
                                                  progress_callback=progress_callback)
        dataset.import_datasource = Datasource({}, datasource_type='upload_storage_tmp', datasource_address="/",
                                               path=upload_response['end_filename'])

        return json.loads(self.client.post(self.service_url, json=dataset.dict()))

    def upload_files_and_post_datasets(self, dataset: Dataset, paths: List[Path],
                                       progress_callback=None) -> dict:
        """Upload multiple files individually (no zipping) and create one dataset from them.

        Every file is uploaded under one shared session key, so they all land in the
        same temporary upload folder on the server; the dataset is then created with
        its datasource pointing at that folder and all files in it are imported.
        Not supported for vector datasets (the server imports vector data from
        archives only). ``progress_callback`` is called with the number of bytes
        sent after each uploaded chunk, across all files.
        """
        paths = [Path(path) for path in paths]
        names = [path.name for path in paths]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f'Files in one dataset must have unique names, got duplicates: {", ".join(duplicates)}')

        flai_upload = upload.FlaiUpload(config=self.config)
        session_key = str(uuid.uuid4())
        for path in paths:
            flai_upload.upload_file(path, dataset.dataset_type_key, session_key=session_key,
                                    progress_callback=progress_callback)

        # all files sit in the {session_key}/ folder; the BE imports the whole folder
        dataset.import_datasource = Datasource({}, datasource_type='upload_storage_tmp', datasource_address="/",
                                               path=session_key)

        return json.loads(self.client.post(self.service_url, json=dataset.dict()))

    def upload_precomputed_copc(self, dataset: Dataset, path: Union[Path, List[Path]],
                               dataset_stats: dict = None, file_stats: list = None,
                               progress_callback=None) -> dict:
        """Upload a pre-computed COPC dataset, skipping server-side preprocessing.

        The path should point to a zip containing (or be a list of):
        - One or more .copc.laz files (point cloud data)
        - overview.copc.laz (reduced-density overview for the viewer)

        Args:
            dataset: Dataset metadata
            path: Path to zip file containing pre-computed COPC files, or a list of
                the COPC file paths to upload individually (no zipping)
            dataset_stats: Optional dataset-level stats dict with keys:
                point_count, point_density, area, classification_hist,
                intensity_hist, num_returns_hist, return_num_hist
            file_stats: Optional list of per-file stats dicts with keys:
                file_name, folder, classification_hist, intensity_hist,
                num_returns_hist, return_num_hist
            progress_callback: Called with the number of bytes sent after each chunk
        """
        dataset.skip_preprocessing = True
        if isinstance(path, (list, tuple)):
            result = self.upload_files_and_post_datasets(dataset, list(path),
                                                         progress_callback=progress_callback)
        else:
            result = self.upload_and_post_datasets(dataset, path, progress_callback=progress_callback)

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
