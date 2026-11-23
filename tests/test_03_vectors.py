import unittest
import warnings

from flai_sdk.api.vectors import FlaiVectors


class RecordingClient:
    """Captures the URL each call would hit, without touching the network."""

    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(('GET', url, kwargs))
        return {}

    def post(self, url, **kwargs):
        self.calls.append(('POST', url, kwargs))
        return {}


def make_service():
    """A FlaiVectors wired to a recording client.

    Built without __init__ on purpose: the real one resolves the active
    organization over HTTP, and these tests are about URL construction, which
    should not need a server to verify.
    """
    service = object.__new__(FlaiVectors)
    service.client = RecordingClient()
    service.service_url = FlaiVectors._get_service_url('https://api.example/api/v1', 'org-1')
    return service


class VectorUrlTests(unittest.TestCase):

    DATASET = 'ds-1'

    def test_service_url_is_the_organization_root(self):
        # The sub-resources hang off the layer, so the service root can no
        # longer be the datasets collection.
        self.assertEqual(
            'https://api.example/api/v1/organization/org-1',
            FlaiVectors._get_service_url('https://api.example/api/v1', 'org-1'),
        )

    def test_features_are_read_from_the_layer(self):
        service = make_service()
        service.get_vector_data(self.DATASET)

        method, url, _ = service.client.calls[0]
        self.assertEqual('GET', method)
        self.assertEqual('https://api.example/api/v1/organization/org-1/vectors/ds-1/features', url)

    def test_field_selection_still_rides_the_query_string(self):
        service = make_service()
        service.get_vector_data(self.DATASET, get_fields='a, b')

        self.assertTrue(service.client.calls[0][1].endswith('/features?data_table_fields=a,b'))

        service = make_service()
        service.get_vector_data(self.DATASET, all_fields=True)
        self.assertTrue(service.client.calls[0][1].endswith('/features?data_table_fields=*'))

    def test_pagination_reaches_the_new_url_too(self):
        # Pagination landed on develop while this branch was moving the URLs.
        # Both have to survive the merge, so both are pinned.
        service = make_service()
        service.get_vector_data(self.DATASET, page=3, page_size=200)

        self.assertEqual(
            'https://api.example/api/v1/organization/org-1/vectors/ds-1/features?page=3&page_size=200',
            service.client.calls[0][1],
        )

    def test_field_selection_and_pagination_combine(self):
        service = make_service()
        service.get_vector_data(self.DATASET, all_fields=True, page=2)

        self.assertEqual(
            'https://api.example/api/v1/organization/org-1/vectors/ds-1/features'
            '?data_table_fields=*&page=2',
            service.client.calls[0][1],
        )

    def test_pages_can_be_walked_in_id_order(self):
        # Without ORDER BY the server's OFFSET pages have no defined order, so a
        # full walk can repeat or miss rows; order_by=id makes it stable.
        service = make_service()
        service.get_vector_data(self.DATASET, all_fields=True, page=2, page_size=5000,
                                order_by='id')

        self.assertEqual(
            'https://api.example/api/v1/organization/org-1/vectors/ds-1/features'
            '?data_table_fields=*&page=2&page_size=5000&order_by=id',
            service.client.calls[0][1],
        )

        service = make_service()
        service.get_vector_data(self.DATASET, order_by='id', order_direction='desc')
        self.assertTrue(service.client.calls[0][1].endswith('/features?order_by=id&order_direction=desc'))

    def test_no_query_string_when_nothing_is_asked_for(self):
        service = make_service()
        service.get_vector_data(self.DATASET)

        self.assertTrue(service.client.calls[0][1].endswith('/features'))

    def test_a_single_feature_is_addressable(self):
        service = make_service()
        service.get_vector_entry(self.DATASET, 42)

        self.assertEqual(
            'https://api.example/api/v1/organization/org-1/vectors/ds-1/features/42',
            service.client.calls[0][1],
        )

    def test_posting_a_feature_goes_to_the_collection(self):
        service = make_service()
        service.post_vector_entry_single(self.DATASET, {'geom': 'POINT(0 0)'})

        method, url, kwargs = service.client.calls[0]
        self.assertEqual('POST', method)
        self.assertEqual('https://api.example/api/v1/organization/org-1/vectors/ds-1/features', url)
        self.assertEqual({'geom': 'POINT(0 0)'}, kwargs['json'])

    def test_schema_reads_the_field_rows(self):
        service = make_service()
        service.get_vector_schema(self.DATASET)

        self.assertEqual(
            'https://api.example/api/v1/organization/org-1/vectors/ds-1/fields',
            service.client.calls[0][1],
        )

    def test_legacy_fields_still_works_and_warns(self):
        # Backward compatibility is the point: the old call keeps hitting the
        # old URL and keeps returning the old shape. It only says so.
        service = make_service()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            service.get_vector_fields(self.DATASET)

        self.assertEqual(
            'https://api.example/api/v1/organization/org-1/datasets/ds-1/vectors/fields',
            service.client.calls[0][1],
        )
        self.assertEqual(1, len(caught))
        self.assertTrue(issubclass(caught[0].category, DeprecationWarning))
        self.assertIn('get_vector_schema', str(caught[0].message))


if __name__ == '__main__':
    unittest.main()
