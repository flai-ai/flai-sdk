from flai_sdk.api import base
from flai_sdk.api.client import Client
from flai_sdk.api.datasets import FlaiDataset
from flai_sdk.models.datasets import LocalHostedDataset, LocalHostedPointcloud


class RecordingClient:
    """Stand-in HTTP client: records calls, returns a canned body."""

    def __init__(self, *, oauth_org="org-1", post_body='{"id": "ds-1"}'):
        self.calls = []
        self._oauth_org = oauth_org
        self._post_body = post_body

    # read_timeout mirrors the real Client: a caller may bound one call more tightly than the
    # process default, and FlaiService resolves the org through get() in its constructor.
    def get(self, url, data=None, json=None, skip_check=False, read_timeout=None):
        self.calls.append(("GET", url, None))
        return {"active_organization_id": self._oauth_org}

    def post(self, url, data=None, json=None, files=[], read_timeout=None):
        self.calls.append(("POST", url, json))
        return self._post_body

    @staticmethod
    def parse_response_from_text(body):
        return Client.parse_response_from_text(body)


def _dataset_service(monkeypatch, post_body='{"id": "ds-1"}'):
    # FlaiService resolves org in __init__, so inject the client *before* construction.
    recording = RecordingClient(post_body=post_body)
    monkeypatch.setattr(base.client, "Client", lambda config: recording)
    return FlaiDataset(access_token="token", api_url="https://api.test")


def test_local_hosted_dataset_posts_metadata_only_payload(monkeypatch):
    service = _dataset_service(monkeypatch, post_body='{"id": "ds-1", "datasource_id": "src-1"}')

    result = service.post_local_hosted_dataset(
        LocalHostedDataset(
            dataset_name="scans",
            unit="meter",
            srid=3794,
            path="scans",
            datasource_url="http://127.0.0.1:8420/tok",
            overview="overview.copc.laz",
            point_count=320,
            pointclouds=[
                LocalHostedPointcloud(
                    filename="tile_1.las",
                    path="tile_1.copc.laz",
                    point_count=320,
                    extent_3d=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                )
            ],
        )
    )

    assert result == {"id": "ds-1", "datasource_id": "src-1"}
    # unset optionals (description, compute_cluster_id, dataset_id, ...) are dropped, nested
    # pointcloud models are serialized, and nothing file-shaped rides along
    assert service.client.calls[-1] == (
        "POST",
        "https://api.test/api/v1/organization/org-1/datasets/local-hosted",
        {
            "dataset_name": "scans",
            "unit": "meter",
            "srid": 3794,
            "path": "scans",
            "datasource_url": "http://127.0.0.1:8420/tok",
            "overview": "overview.copc.laz",
            "point_count": 320,
            "pointclouds": [
                {
                    "filename": "tile_1.las",
                    "path": "tile_1.copc.laz",
                    "point_count": 320,
                    "extent_3d": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                }
            ],
        },
    )
