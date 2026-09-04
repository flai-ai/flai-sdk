from .base import FlaiService


class FlaiVectors(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}/datasets'

    def get_vector_fields(self, dataset_id: str) -> dict:
        return self.client.get(f'{self.service_url}/{dataset_id}/vectors/fields')

    def get_vector_data(self, dataset_id: str, get_fields: str = None, all_fields: bool = False,
                        page: int = None, page_size: int = None) -> dict:
        """Fetch a page of a vector dataset's features.

        The response is {'items': [...], 'pagination': {'page', 'total_pages',
        'total_items', 'page_size'}}, with each item carrying its geometry as
        {'data': <WKT>, 'srid': <int>} under 'geom'. The endpoint always
        paginates (server defaults: page 1, page_size 50), so read
        'pagination.total_pages' and loop to retrieve a whole dataset.
        """

        query = []

        if all_fields:
            query.append('data_table_fields=*')
        elif get_fields is not None:
            query.append(f'data_table_fields={get_fields.replace(" ", "")}')

        if page is not None:
            query.append(f'page={page}')
        if page_size is not None:
            query.append(f'page_size={page_size}')

        return self.client.get(f'{self.service_url}/{dataset_id}/vectors{"?" + "&".join(query) if query else ""}')

    def post_vector_entry_single(self, dataset_id: str, vector_entry: dict) -> dict:
        return self.client.post(f'{self.service_url}/{dataset_id}/vectors', json=vector_entry)
