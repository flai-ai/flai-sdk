from .base import FlaiService
from .client import FlaiApiError
from flai_sdk.models.compute_clusters import (
    ClusterHeartbeat,
    ClusterRegistration,
    ClusterRegistrationResult,
    FlowClaim,
)

STALE_HEAD_EPOCH_ERROR_KEY = 'stale-cluster-head-epoch'


def is_stale_head_epoch_error(exc: Exception) -> bool:
    if not isinstance(exc, FlaiApiError) or exc.status_code != 409:
        return False
    body = getattr(exc, 'response_body', None)
    return STALE_HEAD_EPOCH_ERROR_KEY in str(body if body is not None else exc)


class FlaiComputeClusters(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}/compute-clusters'

    def register(self, registration: ClusterRegistration) -> ClusterRegistrationResult:
        """Create a cluster resource. POST to the org-scoped collection;
        flai-be returns {cluster_id, head_worker_id}. The head_worker_id is for
        cluster health and heartbeat bookkeeping; no processing work runs on the
        head process (num_cpus=0)."""
        response = self.client.parse_response_from_text(
            self.client.post(self.service_url, json=registration.dict(exclude_none=True))
        )
        result = ClusterRegistrationResult()
        result.object_decoder(response or {})
        return result

    def decommission(self, cluster_id: str):
        """Request a graceful decommission (flai-cortex#71): PATCH the cluster to
        ``status=draining``. flai-be validates the active->draining transition,
        stamps ``decommission_requested_at`` and returns
        ``{status, drain_deadline_at}``; the head learns of the drain from its
        next heartbeat response and stops claiming while in-flight flows finish."""
        return self.client.parse_response_from_text(
            self.client.patch(
                f'{self.service_url}/{cluster_id}',
                json={'status': 'draining'},
            )
        )

    def heartbeat(self, cluster_id: str, report: ClusterHeartbeat):
        """Append a liveness event (reported worker state) to the cluster's
        heartbeat stream. Modeled as a created sub-resource rather than a PATCH
        of the cluster so high-frequency telemetry stays separate from the
        cluster's configuration. flai-be stamps last_heartbeat_at server-side."""
        return self.client.parse_response_from_text(
            self.client.post(
                f'{self.service_url}/{cluster_id}/heartbeats',
                json=report.dict(exclude_none=True),
            )
        )

    def claim_next_flows(self, cluster_id: str, max_flows: int = None,
                         head_epoch: int = None) -> list:
        """Lease pending flows routed to this cluster, up to ``max_flows``.

        flai-be returns a batch envelope ``{flows: [<flow>, ...]}`` (each row
        already marked PUBLISHED). ``max_flows`` is the head's free-slot hint
        sent in the request body; today's flow-claims route ignores unknown
        body fields, so it is advisory until the BE honors it. ``head_epoch``
        is the fencing token (flai-cortex#68) — a stale value raises the 409
        :func:`is_stale_head_epoch_error` rejection. Returns a list of
        :class:`FlowClaim` (empty on 204 / empty body)."""
        body = {}
        if max_flows is not None:
            body['max_flows'] = max_flows
        if head_epoch is not None:
            body['head_epoch'] = head_epoch
        body = body or None
        response = self.client.parse_response_from_text(
            self.client.post(f'{self.service_url}/{cluster_id}/flow-claims', json=body)
        )
        if not response:  # 204 / empty body -> idle
            return []
        rows = response.get('flows', []) if isinstance(response, dict) else response
        claims = []
        for row in rows:
            claim = FlowClaim()
            claim.object_decoder(row)
            # BE currently sends the owner token as cli_sdk_token; tolerate a future rename.
            claim.user_token = row.get('user_token') or row.get('cli_sdk_token')
            claims.append(claim)
        return claims
