import os
from math import isfinite

from flai_sdk.models.base import BaseModel


class BillingValue(BaseModel):

    def __init__(self, resource: str, value):
        self.resource = resource
        self.value = value


class NodeBilling(BaseModel):
    """Billing rolled up at node completion.

    Matches the flai-be contract: a runtime tag plus a list of
    ``{resource, value}`` measurements - the same shape the per-file path
    sends via ``tools.utils_api.create_billing_payload``.
    """

    def __init__(self, values: list = None, runtime_environment: str = None):
        self.runtime_environment = runtime_environment or os.getenv('RUNTIME_ENVIRONMENT', 'local')
        self.values = values if values is not None else []

    @classmethod
    def from_resources(cls, area=None, point_count=None, datasize=None, runtime_environment=None):
        """Build the resource list from the common point-cloud measurements,
        mirroring the per-file ``create_billing_payload`` helper."""
        values = []
        if area is not None and isfinite(area) and float(area) >= 0:
            values.append(BillingValue('unique_files_area', float(abs(area))))
        if point_count is not None and isfinite(point_count) and int(point_count) >= 0:
            values.append(BillingValue('unique_files_point_count', int(abs(point_count))))
        if datasize is not None and isfinite(datasize) and float(datasize) >= 0:
            values.append(BillingValue('unique_files_datasize', float(abs(datasize))))
        return cls(values=values, runtime_environment=runtime_environment)


class NodeExecutionUpdate(BaseModel):
    """Base partial update for a flow-node-execution row."""

    def __init__(self, status: str = None, message: str = None,
                 started_at: str = None, finished_at: str = None):
        self.status = status
        self.message = message
        self.started_at = started_at
        self.finished_at = finished_at


class NodeStarted(NodeExecutionUpdate):

    def __init__(self, started_at: str = None, task_id: str = None, message: str = None):
        super().__init__(status='processing', message=message, started_at=started_at)
        self.task_id = task_id


class NodeProgress(NodeExecutionUpdate):
    # node stays 'processing'; flai-be requires `status` on every update, so we
    # re-send it (merge-on-present means this never changes the row).

    def __init__(self, progress: float = None, files_total: int = None,
                 files_completed: int = None, files_failed: int = None, message: str = None):
        super().__init__(status='processing', message=message)
        self.progress = progress
        self.files_total = files_total
        self.files_completed = files_completed
        self.files_failed = files_failed


class NodeCompleted(NodeExecutionUpdate):

    def __init__(self, billing: NodeBilling = None, output_metadata: dict = None,
                 execution_time: float = None, finished_at: str = None, message: str = None,
                 node_response: dict = None,
                 main_peak_memory_bytes: int = None, main_memory_budget_bytes: int = None,
                 file_peak_memory_bytes: int = None, file_memory_budget_bytes: int = None,
                 file_peak_filename: str = None,
                 main_cpu_booked: float = None, main_cpu_used_cores: float = None,
                 file_cpu_booked: float = None, file_cpu_used_cores: float = None):
        super().__init__(status='finished', message=message, finished_at=finished_at)
        self.billing = billing
        self.output_metadata = output_metadata
        self.execution_time = execution_time
        self.node_response = node_response
        self.main_peak_memory_bytes = main_peak_memory_bytes
        self.main_memory_budget_bytes = main_memory_budget_bytes
        self.file_peak_memory_bytes = file_peak_memory_bytes
        self.file_memory_budget_bytes = file_memory_budget_bytes
        self.file_peak_filename = file_peak_filename
        # CPU counterpart of the memory pair. `booked` is the tier's num_cpus,
        # `used_cores` is CPU-seconds over wall-seconds. Both layers stay
        # separate for the same reason memory does: the remedy differs.
        self.main_cpu_booked = main_cpu_booked
        self.main_cpu_used_cores = main_cpu_used_cores
        self.file_cpu_booked = file_cpu_booked
        self.file_cpu_used_cores = file_cpu_used_cores


class NodeFailed(NodeExecutionUpdate):

    def __init__(self, error: str = None, traceback: str = None, billing: NodeBilling = None,
                 finished_at: str = None, message: str = None, node_response: dict = None,
                 main_peak_memory_bytes: int = None, main_memory_budget_bytes: int = None,
                 file_peak_memory_bytes: int = None, file_memory_budget_bytes: int = None,
                 file_peak_filename: str = None,
                 main_cpu_booked: float = None, main_cpu_used_cores: float = None,
                 file_cpu_booked: float = None, file_cpu_used_cores: float = None):
        # flai-be persists the failure reason in `message`; `error`/`traceback`
        # have no v1 column, so fold `error` into `message` (when no explicit
        # message is given) instead of losing it on the wire. `error`/`traceback`
        # are kept as forward-compat attributes (dropped server-side in v1;
        # `traceback` routes to logs in a later phase).
        super().__init__(status='failed', message=message or error, finished_at=finished_at)
        self.error = error
        self.traceback = traceback
        self.billing = billing
        self.node_response = node_response
        self.main_peak_memory_bytes = main_peak_memory_bytes
        self.main_memory_budget_bytes = main_memory_budget_bytes
        self.file_peak_memory_bytes = file_peak_memory_bytes
        self.file_memory_budget_bytes = file_memory_budget_bytes
        self.file_peak_filename = file_peak_filename
        self.main_cpu_booked = main_cpu_booked
        self.main_cpu_used_cores = main_cpu_used_cores
        self.file_cpu_booked = file_cpu_booked
        self.file_cpu_used_cores = file_cpu_used_cores


class FlowExecutionLogEntry(BaseModel):
    """One cortex log line for POST /flow-executions/{id}/logs (#54).

    ``message`` carries the full cortex JSON envelope line; the sidecar fields
    (timestamp, level, service_name, flow_node_execution_id) are what flai-be
    indexes into flow_execution_logs columns.
    """

    def __init__(self, timestamp: str = None, level: str = None, service_name: str = None,
                 message: str = None, flow_node_execution_id: str = None, event_id: str = None):
        self.timestamp = timestamp
        self.level = level
        self.service_name = service_name
        self.message = message
        self.flow_node_execution_id = flow_node_execution_id
        # flai-cortex#146: one UUID per captured record, stable across retries; flai-be
        # deduplicates a redelivered batch on it. Optional for legacy senders.
        self.event_id = event_id


class FlowExecutionLogBatch(BaseModel):
    """A batch of :class:`FlowExecutionLogEntry` (or plain dicts) to flush."""

    def __init__(self, logs: list = None):
        self.logs = logs if logs is not None else []


class ComputeClusterLogEntry(BaseModel):
    """One cortex cluster-channel log line for POST /compute-clusters/{id}/logs (flai-cortex#146).

    Same envelope contract as :class:`FlowExecutionLogEntry`: ``message`` carries the
    full cortex JSON line; the sidecar fields are what flai-be indexes into
    compute_cluster_logs columns. ``node_role`` is head/worker/cli; ``ray_node_id``
    lets flai-be map the line onto a compute_cluster_workers row.
    """

    def __init__(self, timestamp: str = None, level: str = None, service_name: str = None,
                 message: str = None, node_role: str = None, ray_node_id: str = None,
                 compute_cluster_worker_id: str = None, event_id: str = None):
        self.timestamp = timestamp
        self.level = level
        self.service_name = service_name
        self.message = message
        self.node_role = node_role
        self.ray_node_id = ray_node_id
        self.compute_cluster_worker_id = compute_cluster_worker_id
        self.event_id = event_id


class ComputeClusterLogBatch(BaseModel):
    """A batch of :class:`ComputeClusterLogEntry` (or plain dicts) to flush."""

    def __init__(self, logs: list = None):
        self.logs = logs if logs is not None else []
