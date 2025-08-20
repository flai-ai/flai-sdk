from .base import FlaiService


class FlaiVectors(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}/datasets'

    def get_vector_fields(self, dataset_id: str) -> dict:
        return self.client.get(f'{self.service_url}/{dataset_id}/vectors/fields')

    def get_vector_data(self, dataset_id: str, get_fields: str = None, all_fields: bool = False) -> dict:

        fields_query = '?data_table_fields='

        if all_fields:
            fields_query += f'{"*"}'
        elif get_fields is not None:
            fields_query += f'{get_fields.replace(" ", "")}'

        return self.client.get(f'{self.service_url}/{dataset_id}/vectors{fields_query if not fields_query.endswith("=") else ""}')

    def post_vector_entry_single(self, dataset_id: str, vector_entry: dict) -> dict:
        return self.client.post(f'{self.service_url}/{dataset_id}/vectors', json=vector_entry)
