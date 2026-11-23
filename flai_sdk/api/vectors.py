import warnings

from .base import FlaiService


class FlaiVectors(FlaiService):
    """Vector layers: their features and their attribute schema.

    A layer's sub-resources hang off the layer itself::

        organization/{org}/vectors/{dataset_id}/features
        organization/{org}/vectors/{dataset_id}/fields

    The older URLs nested these under ``datasets/{id}/vectors``, which put
    ``fields`` in the same slot as a feature id. They still work and keep
    working — no removal date is announced — but they answer with a
    ``Deprecation`` header and a ``Link`` to the replacement.
    """

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}'

    def _layer_url(self, dataset_id: str) -> str:
        return f'{self.service_url}/vectors/{dataset_id}'

    def get_vector_schema(self, dataset_id: str) -> dict:
        """The layer's attribute schema, as a list of fields.

        Each field carries what it is and where its value comes from::

            data_type  text | long_text | integer | decimal | float
                       | boolean | date | json
            source     manual | pointcloud | expression | relation
                       | relation_key

        plus ``name``, ``label``, ``position`` and the source-specific bits
        (``expression``, ``relation_id``, ``source_attribute``, ...).

        This is the representation to build against. ``get_vector_fields``
        returns the same fields as a shapefile DBF descriptor map, which cannot
        express any of the above.
        """
        return self.client.get(f'{self._layer_url(dataset_id)}/fields')

    def get_vector_fields(self, dataset_id: str) -> dict:
        """The layer's fields as a ``{name: {type, size, decimals}}`` map.

        .. deprecated::
            Use :meth:`get_vector_schema`. The DBF descriptor is a shapefile
            artifact: it has no field identity, no ordering, no labels, and no
            way to say a field is computed or looked up from another layer.

            Still returned unchanged, and still the shape
            ``create_vector_without_file_datasets`` accepts, so nothing has to
            move today.
        """
        warnings.warn(
            'get_vector_fields() returns the legacy DBF descriptor map and its endpoint is '
            'deprecated; use get_vector_schema() for the full field definitions.',
            DeprecationWarning,
            stacklevel=2,
        )

        return self.client.get(f'{self.service_url}/datasets/{dataset_id}/vectors/fields')

    def get_vector_data(self, dataset_id: str, get_fields: str = None, all_fields: bool = False,
                        page: int = None, page_size: int = None, order_by: str = None,
                        order_direction: str = None) -> dict:
        """Fetch a page of a vector dataset's features.

        The response is {'items': [...], 'pagination': {'page', 'total_pages',
        'total_items', 'page_size'}}, with each item carrying its geometry and
        its row 'id'. The geometry sits under 'geom' as {'data': <WKT>, 'srid': <int>}.
        The endpoint always paginates (server defaults: page 1, page_size 50), so
        read 'pagination.total_pages' and loop to retrieve a whole dataset.

        Without 'order_by' the rows come in no defined order, so a walk over
        several pages can repeat or miss rows. Pass order_by='id' for a stable walk.
        'order_direction' is 'asc' (server default) or 'desc'.
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
        if order_by is not None:
            query.append(f'order_by={order_by}')
            if order_direction is not None:
                query.append(f'order_direction={order_direction}')

        return self.client.get(
            f'{self._layer_url(dataset_id)}/features'
            f'{"?" + "&".join(query) if query else ""}'
        )

    def get_vector_entry(self, dataset_id: str, feature_id: int) -> dict:
        return self.client.get(f'{self._layer_url(dataset_id)}/features/{feature_id}')

    def post_vector_entry_single(self, dataset_id: str, vector_entry: dict) -> dict:
        return self.client.post(f'{self._layer_url(dataset_id)}/features', json=vector_entry)
