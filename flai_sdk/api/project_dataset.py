from .base import FlaiService
from flai_sdk.models.project_dataset import ProjectDataset


class FlaiProjectDataset(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/organization/{active_org_id}/project_datasets"

    def get_project_datasets(self):
        return self.client.get(self.service_url)

    def post_project_dataset(self, project_dataset: ProjectDataset) -> dict:
        return self.client.post(self.service_url, json=project_dataset.dict())
