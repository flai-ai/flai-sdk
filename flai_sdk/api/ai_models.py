import json
from .base import FlaiService
from flai_sdk.api import upload
from pathlib import Path
from flai_sdk.models.ai_models import AiModel
from flai_sdk.models.datasets import Datasource
from flai_sdk.models.ai_training_sessions import CliAiTrainingSession, CliAiTrainingSessionPatch, AiTrainingSessionStatusUpdate


class FlaiAiModel(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/ai-models'

    def get_stored_in_organization(self, model_id: str):
        data = self.client.get(f'{self.service_url}/{model_id}/stored-in-organization')
        return data['organization_id']

    def get_ai_model_files(self, model_id: str):
        data = self.client.get(f'{self.service_url}/{model_id}/files')
        return data['files']

    def upload_ai_model(self, ai_model: AiModel, model_zip_path: Path):

        flai_upload = upload.FlaiUpload()
        upload_response = flai_upload.upload_file(model_zip_path, 'ai_model')

        ai_model.import_datasource = Datasource({}, datasource_type='upload_storage_tmp', datasource_address="/",
                                                path=upload_response['end_filename'])

        return json.loads(self.client.post(self.service_url, json=ai_model.dict()))

    def create_cli_ai_training_session(self, ai_training_session: CliAiTrainingSession) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/cli-ai-training-session',
                                           json=ai_training_session.dict()))

    def patch_ai_training_session(self, ai_session_id: str, ai_training_session_patch: CliAiTrainingSessionPatch) -> dict:
        return json.loads(self.client.put(f'{self.service_url}/ai-training-sessions/{ai_session_id}',
                                          json=ai_training_session_patch.dict()))

    def update_ai_training_session_status(self, ai_training_session_status_update: AiTrainingSessionStatusUpdate) -> dict:
        return json.loads(self.client.post(f'{self.service_url}/ai-training-sessions/status-update',
                                          json=ai_training_session_status_update.dict()))

    def get_model_info(self, model_id: str):
        return self.client.get(f'{self.service_url}/{model_id}')

    def get_semantic_definitions(self, model_id: str):
        data = self.client.get(f'{self.service_url}/{model_id}?decorators=semantic_labels_definition')
        return data['semantic_labels_definition']
