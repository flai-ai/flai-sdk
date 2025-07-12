import json
from .base import FlaiService
from flai_sdk.models.semantic_definition_schemas import GenericSemanticDefinitionSchema


class SemanticDefinitionSchemasModel(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/semantic-definition-schemas'

    def get_semantic_definitions(self, semantic_definition_schema_id: str):
        sd = self.client.get(f'{self.service_url}/{semantic_definition_schema_id}/semantic-definitions')
        # make it in the same format as it was before the semantic rework
        return {s['code']: s for s in sd}

    def create_generic_schema(self, generic_schema: GenericSemanticDefinitionSchema):
        return json.loads(self.client.post(f'{self.service_url}/create-generic-schema', json=generic_schema.dict()))
