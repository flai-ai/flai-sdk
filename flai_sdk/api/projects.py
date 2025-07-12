from .base import FlaiService
from flai_sdk.models.projects import Project
import json

class FlaiProject(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str) -> str:
        return f"{base_url}/projects"

    def get_projects(self):
        return self.client.get(self.service_url)

    def get_project(self, project_id: str):
        return self.client.get(f'{self.service_url}/{project_id}')

    def post_project(self, project: Project) -> dict:
        return json.loads(self.client.post(self.service_url, json=project.dict()))
