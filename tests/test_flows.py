from flai_sdk.api import base
from flai_sdk.api.flows import FlaiFlows


class RecordingClient:
    """Stand-in HTTP client: records the requested urls, returns a canned body."""

    def __init__(self):
        self.urls = []

    def get(self, url, data=None, json=None, skip_check=False, read_timeout=None):
        self.urls.append(url)
        if url.endswith('/oauth/me'):
            return {'active_organization_id': 'org-1'}
        return {'items': [], 'pagination': {}}


def _flows_service(monkeypatch):
    # FlaiService resolves the organization in __init__, so inject the client before construction.
    recording = RecordingClient()
    monkeypatch.setattr(base.client, 'Client', lambda config: recording)
    return FlaiFlows(access_token='token', api_url='https://api.test'), recording


def test_get_flows_lists_flows_of_the_active_organization(monkeypatch):
    service, recording = _flows_service(monkeypatch)

    result = service.get_flows()

    assert recording.urls[-1] == 'https://api.test/api/v1/organization/org-1/flows'
    assert result == {'items': [], 'pagination': {}}


def test_get_flows_passes_paging(monkeypatch):
    service, recording = _flows_service(monkeypatch)

    service.get_flows(page=2, page_size=10)

    assert recording.urls[-1] == 'https://api.test/api/v1/organization/org-1/flows?page=2&page_size=10'
