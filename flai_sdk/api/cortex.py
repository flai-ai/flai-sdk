from .base import FlaiService
from flai_sdk.models.cortex import (
    NodeExecutionUpdate, NodeStarted, NodeProgress, NodeCompleted, NodeFailed,
    FlowExecutionLogBatch,
)


class FlaiCortex(FlaiService):
    """Cortex -> flai-be callbacks for the node-execution lifecycle.

    Uses the universal status endpoint
    ``PATCH /api/v1/organization/{org_id}/flow-node-executions/{flow_node_execution_id}``
    (flai-be #169), which drives the whole node lifecycle: ``processing`` persists
    the row; ``finished`` / ``failed`` run the full completion / failure
    orchestration (incl. flow-level finalization). ``org_id`` is resolved from
    ``/oauth/me`` by :class:`FlaiService`. The id is a global primary key, so the
    parent ``flow_execution_id`` is not needed to address the row and is omitted
    from the route. Every lifecycle event (started, progress, completed, failed)
    PATCHes a typed :class:`NodeExecutionUpdate` with only the changed fields.
    Status strings follow the SDK convention used by the per-file reporting:
    ``processing`` / ``finished`` / ``failed``.
    """

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}'

    def _patch_node(self, flow_node_execution_id: str, update: NodeExecutionUpdate):
        body = update.dict(exclude_none=True)
        return self.client.parse_response_from_text(
            self.client.patch(
                f'{self.service_url}/flow-node-executions/{flow_node_execution_id}',
                json=body,
            )
        )

    def node_started(self, flow_node_execution_id: str, update: NodeStarted = None):
        return self._patch_node(flow_node_execution_id, update or NodeStarted())

    def node_progress(self, flow_node_execution_id: str, update: NodeProgress = None):
        return self._patch_node(flow_node_execution_id, update or NodeProgress())

    def node_completed(self, flow_node_execution_id: str, update: NodeCompleted = None):
        return self._patch_node(flow_node_execution_id, update or NodeCompleted())

    def node_failed(self, flow_node_execution_id: str, update: NodeFailed = None):
        return self._patch_node(flow_node_execution_id, update or NodeFailed())

    def send_flow_execution_logs(self, flow_execution_id: str, batch: FlowExecutionLogBatch):
        """POST a batch of cortex log lines to flai-be (#54).

        Single-attempt on purpose (``post_once``): the cortex log flusher owns
        retry (re-queue and retry next tick), so tenacity's multi-minute
        backoff must not pin its flush thread. Note ``FlaiService.__init__``
        still resolves the org via one retried ``GET /oauth/me``; build the
        service lazily on a background thread.
        """
        return self.client.parse_response_from_text(
            self.client.post_once(
                f'{self.service_url}/flow-executions/{flow_execution_id}/logs',
                json=batch.dict(exclude_none=True),
            )
        )
