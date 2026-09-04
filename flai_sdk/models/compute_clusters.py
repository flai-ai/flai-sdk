from flai_sdk.models.base import BaseModel


class WorkerReport(BaseModel):
    """One entry in a heartbeat's worker list (from `ray list_nodes`)."""

    def __init__(self, hostname: str = None, ray_node_id: str = None,
                 reported_resources: dict = None, status: str = None,
                 health_checks: list = None):
        self.hostname = hostname
        self.ray_node_id = ray_node_id
        self.reported_resources = reported_resources
        self.status = status
        self.health_checks = health_checks


class ClusterRegistration(BaseModel):

    def __init__(self, hostname: str, cortex_version: str, head_ray_node_id: str,
                 name: str = None, ray_dashboard_url: str = None,
                 ray_namespace: str = None, is_public: bool = None,
                 infrastructure: str = None, is_default: bool = None,
                 on_decommission: str = None, cluster_key: str = None):
        self.hostname = hostname
        self.cortex_version = cortex_version
        self.head_ray_node_id = head_ray_node_id
        self.name = name
        self.ray_dashboard_url = ray_dashboard_url
        self.ray_namespace = ray_namespace
        self.is_public = is_public
        self.infrastructure = infrastructure
        self.is_default = is_default
        self.on_decommission = on_decommission
        self.cluster_key = cluster_key


class ClusterHeartbeat(BaseModel):

    def __init__(self, workers: list = None, status: str = None,
                 resources_total: dict = None, resources_available: dict = None,
                 node_count: int = None, head_epoch: int = None,
                 active_flows: int = None):
        self.workers = workers if workers is not None else []
        self.status = status
        self.resources_total = resources_total
        self.resources_available = resources_available
        self.node_count = node_count
        self.head_epoch = head_epoch
        self.active_flows = active_flows


class ClusterRegistrationResult(BaseModel):
    """Typed ``POST /organization/{org_id}/compute-clusters`` response (201):
    ``{cluster_id, head_worker_id, head_epoch}``.

    Constructed empty and filled from the parsed response via the inherited
    ``object_decoder``; missing keys keep their ``None`` default. ``head_epoch``
    is the fencing token to echo on heartbeats/claims (flai-cortex#68); older
    BEs omit it.
    """

    def __init__(self, cluster_id: str = None, head_worker_id: str = None,
                 head_epoch: int = None):
        self.cluster_id = cluster_id
        self.head_worker_id = head_worker_id
        self.head_epoch = head_epoch


class FlowClaim(BaseModel):
    """Typed ``POST /organization/{org_id}/compute-clusters/{id}/flow-claims`` response (200).

    A claim leases the next pending flow for a cluster. The token rides under
    ``user_token`` (the flow-owner token); the claim carries no ``api_url`` (the
    head supplies ``FLAI_HOST`` from its own config) and no ``organization_id``
    (the worker resolves org from ``user_token`` via ``/oauth/me``).
    """

    def __init__(self, flow_execution_id: str = None, flow_json: dict = None,
                 start_nodes_ids: list = None, user_token: str = None,
                 cli_license_id: str = None, resume_from_node: str = None):
        self.flow_execution_id = flow_execution_id
        self.flow_json = flow_json
        self.start_nodes_ids = start_nodes_ids
        self.user_token = user_token
        self.cli_license_id = cli_license_id
        self.resume_from_node = resume_from_node

    def to_payload(self) -> dict:
        """Return the plain Mapping the Ray ``FlowExecutorActor`` consumes.

        The actor reads the flow via ``extract_flow_spec`` (``flow_json``) and
        resolves auth from ``user_token``; it must be fed a dict, never this
        model object.
        """
        return {
            'flow_execution_id': self.flow_execution_id,
            'flow_json': self.flow_json,
            'start_nodes_ids': self.start_nodes_ids,
            'user_token': self.user_token,
            'cli_license_id': self.cli_license_id,
            'resume_from_node': self.resume_from_node,
        }
