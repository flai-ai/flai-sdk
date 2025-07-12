import os
from flai_sdk.models import flow_executions
from flai_sdk.api import flow_executions as flow_executions_api
import xxhash


class ComputeHash:
    def __init__(self):
        self.hasher = xxhash.xxh3_128()

    def update(self, data):
        return self.hasher.update(data)

    def compute_hash(self):
        hash_value = self.hasher.hexdigest()
        self.reset()
        return hash_value

    def reset(self):
        return self.hasher.reset()

def get_hash(data):

    if not os.getenv('FLAI_ENABLE_ON_THE_FLY_PER_FILE_HASH_COMPUTATION', True):
        return None

    hasher = ComputeHash()
    hasher.update(data)
    return hasher.compute_hash()


def create_billing_payload(area, point_count):
    payload = {
        'runtime_environment': os.getenv('RUNTIME_ENVIRONMENT', 'local'),
        'values': [
        ]
    }

    if area is not None and float(area) >= 0:
        payload['values'].append({
            'resource': 'unique_files_area',
            'value': float(abs(area)),
        })

    if point_count is not None and int(point_count) >= 0:
        payload['values'].append({
            'resource': 'unique_files_point_count',
            'value': int(abs(point_count)),
        })

    return payload


def start_and_check_file_processing(*args, data_to_hash=None, **kwargs):

    report_enable = bool(int(os.getenv('FLAI_ENABLE_PER_FILE_STATUS_LOG_REPORTING', 1)))
    if not report_enable:
        return

    billing_payload = {}
    if kwargs.get('area') is not None or kwargs.get('point_count') is not None:
        billing_payload = create_billing_payload(kwargs['area'], kwargs['point_count'])

    return flow_executions_api.FlaiFlowExecutions().post_check_file_processing(
        flow_executions.CheckProcessingFlowNodeExecutionFile(
            flow_node_execution_id=str(kwargs['flow_node_execution_id']),
            filename=str(kwargs['filename']),
            storage_type=str(kwargs.get('storage_type')),
            dataset_id=kwargs.get('dataset_id', None),
            file_hash=kwargs.get('file_hash') if data_to_hash is None else get_hash(data_to_hash),
            status=str(kwargs.get('status', 'processing')),
            message=kwargs.get('message'),
            task_name=str(kwargs.get('task_name')),
            billing=billing_payload,
        )
    )


def finish_file_processing(*args, **kwargs):

    return start_and_check_file_processing(*args, status='finished', **kwargs)


def failed_file_processing(*args, **kwargs):

    return start_and_check_file_processing(*args, status='failed', **kwargs)
