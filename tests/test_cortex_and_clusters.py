from types import SimpleNamespace

from flai_sdk.api import base
from flai_sdk.api.client import Client
from flai_sdk.api.compute_clusters import FlaiComputeClusters
from flai_sdk.api.cortex import FlaiCortex
from flai_sdk.models.compute_clusters import (
    ClusterHeartbeat,
    ClusterRegistration,
    ClusterRegistrationResult,
    FlowClaim,
)
from flai_sdk.models.cortex import NodeCompleted, NodeFailed
from flai_sdk.models.flow_executions import CheckProcessingFlowNodeExecutionFile


class RecordingClient:
    """Stand-in HTTP client: records calls, returns a canned body.

    ``oauth_org`` set => the org-scoped ``FlaiService`` resolves org via
    ``/oauth/me`` on construction; ``None`` => assert a token-scoped client never
    makes that call.
    """

    def __init__(self, *, oauth_org=None, post_body='{"ok": true}'):
        self.calls = []
        self._oauth_org = oauth_org
        self._post_body = post_body

    def get(self, url, data=None, json=None, skip_check=False):
        if self._oauth_org is None:
            raise AssertionError("token-scoped clients must not call /oauth/me")
        self.calls.append(("GET", url, None))
        return {"active_organization_id": self._oauth_org}

    def post(self, url, data=None, json=None, files=[]):
        self.calls.append(("POST", url, json))
        return self._post_body

    def patch(self, url, data=None, json=None, files=[]):
        self.calls.append(("PATCH", url, json))
        return self._post_body

    @staticmethod
    def parse_response_from_text(body):
        return Client.parse_response_from_text(body)


def _cortex_service(monkeypatch, recording):
    # FlaiService resolves org in __init__, so inject the client *before*
    # construction by patching the Client the service builds.
    monkeypatch.setattr(base.client, "Client", lambda config: recording)
    return FlaiCortex(access_token="token", api_url="https://api.test")


def _cluster_service(monkeypatch, post_body='{"ok": true}'):
    # FlaiComputeClusters is org-scoped (FlaiService), so it resolves org in
    # __init__. Inject the client *before* construction, like the cortex helper.
    recording = RecordingClient(oauth_org="org-1", post_body=post_body)
    monkeypatch.setattr(base.client, "Client", lambda config: recording)
    return FlaiComputeClusters(access_token="token", api_url="https://api.test")


def test_cortex_node_lifecycle_posts_to_org_scoped_route(monkeypatch):
    recording = RecordingClient(oauth_org="org-1")
    service = _cortex_service(monkeypatch, recording)

    assert service.node_completed("node-exec-1", NodeCompleted(message="done")) == {"ok": True}

    # org resolved via /oauth/me, then a PATCH to the universal status endpoint (#169)
    assert recording.calls == [
        ("GET", "https://api.test/api/v1/oauth/me", None),
        (
            "PATCH",
            "https://api.test/api/v1/organization/org-1/flow-node-executions/node-exec-1",
            {"status": "finished", "message": "done"},
        ),
    ]


def test_cortex_node_failed_folds_error_into_message(monkeypatch):
    recording = RecordingClient(oauth_org="org-1")
    service = _cortex_service(monkeypatch, recording)

    service.node_failed("node-exec-1", NodeFailed(error="boom"))

    # the failure reason rides in `message` (flai-be has no `error` column); the
    # forward-compat `error` field is still sent and dropped server-side.
    post_call = recording.calls[-1]
    assert post_call[0] == "PATCH"
    assert post_call[2] == {"status": "failed", "message": "boom", "error": "boom"}


def test_cortex_node_response_rides_completed_and_failed(monkeypatch):

    recording = RecordingClient(oauth_org="org-1")
    service = _cortex_service(monkeypatch, recording)

    report = {"tile_1.laz": {"validated": False, "description": ["Zero points in las header"]}}
    service.node_completed(
        "node-exec-1",
        NodeCompleted(output_metadata={"srid": 3857}, node_response=report),
    )
    assert recording.calls[-1][2] == {
        "status": "finished",
        "output_metadata": {"srid": 3857},
        "node_response": report,
    }

    service.node_failed("node-exec-1", NodeFailed(error="boom", node_response=report))
    assert recording.calls[-1][2] == {
        "status": "failed",
        "message": "boom",
        "error": "boom",
        "node_response": report,
    }


def test_compute_cluster_routes_are_org_scoped_posts(monkeypatch):
    service = _cluster_service(monkeypatch)

    service.register(
        ClusterRegistration(hostname="host-a", cortex_version="1.2.3", head_ray_node_id="ray-head-1")
    )
    service.heartbeat("cluster-1", ClusterHeartbeat(workers=[{"ray_node_id": "ray-1"}]))
    service.claim_next_flows("cluster-1")

    # org resolved via /oauth/me on construction, then POSTs to the org-scoped routes
    assert service.client.calls == [
        ("GET", "https://api.test/api/v1/oauth/me", None),
        (
            "POST",
            "https://api.test/api/v1/organization/org-1/compute-clusters",
            {"hostname": "host-a", "cortex_version": "1.2.3", "head_ray_node_id": "ray-head-1"},
        ),
        (
            "POST",
            "https://api.test/api/v1/organization/org-1/compute-clusters/cluster-1/heartbeats",
            {"workers": [{"ray_node_id": "ray-1"}]},
        ),
        (
            "POST",
            "https://api.test/api/v1/organization/org-1/compute-clusters/cluster-1/flow-claims",
            None,
        ),
    ]


def test_register_includes_privileged_fields_only_when_set(monkeypatch):
    service = _cluster_service(monkeypatch)

    service.register(
        ClusterRegistration(
            hostname="host-a", cortex_version="1.2.3", head_ray_node_id="ray-head-1",
            is_public=True, infrastructure="aws", is_default=True,
            on_decommission="terminate-instance",
        )
    )

    register_call = service.client.calls[-1]
    assert register_call[2] == {
        "hostname": "host-a",
        "cortex_version": "1.2.3",
        "head_ray_node_id": "ray-head-1",
        "is_public": True,
        "infrastructure": "aws",
        "is_default": True,
        "on_decommission": "terminate-instance",
    }


def test_decommission_patches_status_draining(monkeypatch):
    service = _cluster_service(monkeypatch, post_body='{"status": "draining", "drain_deadline_at": "2026-07-17T07:00:00Z"}')

    result = service.decommission("cluster-1")

    assert result == {"status": "draining", "drain_deadline_at": "2026-07-17T07:00:00Z"}
    assert service.client.calls[-1] == (
        "PATCH",
        "https://api.test/api/v1/organization/org-1/compute-clusters/cluster-1",
        {"status": "draining"},
    )


def test_heartbeat_reports_active_flows_while_draining(monkeypatch):
    service = _cluster_service(monkeypatch)

    service.heartbeat("cluster-1", ClusterHeartbeat(status="draining", active_flows=2))

    beat = service.client.calls[-1]
    assert beat[2]["status"] == "draining"
    assert beat[2]["active_flows"] == 2


def test_register_returns_typed_result(monkeypatch):
    service = _cluster_service(monkeypatch, post_body='{"cluster_id": "c1", "head_worker_id": "w1"}')

    result = service.register(
        ClusterRegistration(hostname="h", cortex_version="1", head_ray_node_id="ray-head-1")
    )

    assert isinstance(result, ClusterRegistrationResult)
    assert (result.cluster_id, result.head_worker_id) == ("c1", "w1")


def test_claim_next_flows_returns_typed_batch(monkeypatch):
    # BE returns a {flows:[...]} batch; the owner token rides as cli_sdk_token today.
    body = (
        '{"flows": ['
        '{"flow_execution_id": "fe1", "flow_json": {"id": "f1"}, '
        '"start_nodes_ids": ["n1"], "cli_sdk_token": "owner-token"}, '
        '{"flow_execution_id": "fe2", "flow_json": {"id": "f2"}, '
        '"start_nodes_ids": ["n2"], "cli_sdk_token": "owner-token-2"}'
        ']}'
    )
    service = _cluster_service(monkeypatch, post_body=body)

    claims = service.claim_next_flows("cluster-1", max_flows=5)

    assert [c.flow_execution_id for c in claims] == ["fe1", "fe2"]
    # cli_sdk_token is mapped onto user_token (the name the executor consumes)
    assert [c.user_token for c in claims] == ["owner-token", "owner-token-2"]
    # to_payload() hands the actor a plain dict carrying the flow envelope + token
    payload = claims[0].to_payload()
    assert payload["flow_json"] == {"id": "f1"}
    assert payload["user_token"] == "owner-token"
    # the free-slot hint rides in the request body
    assert service.client.calls[-1] == (
        "POST",
        "https://api.test/api/v1/organization/org-1/compute-clusters/cluster-1/flow-claims",
        {"max_flows": 5},
    )


def test_claim_next_flows_returns_empty_list_when_queue_empty(monkeypatch):
    service = _cluster_service(monkeypatch, post_body="")  # 204 / empty body

    assert service.claim_next_flows("cluster-1") == []


def test_explicit_config_injection_does_not_require_env_priority_change(monkeypatch):
    monkeypatch.setattr(base.client, "Client", lambda config: RecordingClient(oauth_org="org-1"))

    service = FlaiCortex(access_token="explicit-token", api_url="https://explicit.test")

    assert service.config.flai_access_token == "explicit-token"
    assert service.config.flai_host == "https://explicit.test"


def test_client_accepts_2xx_and_empty_204():
    assert Client.parse_response(SimpleNamespace(status_code=204, content=b"", text="")) is None
    assert Client.parse_response_from_text('{"ok": true}') == {"ok": True}


def test_check_processing_payload_allows_ray_node_id():
    payload = CheckProcessingFlowNodeExecutionFile(
        flow_node_execution_id="exec-node-1",
        filename="tile.laz",
        ray_node_id="ray-node-1",
    )

    assert payload.dict()["ray_node_id"] == "ray-node-1"
