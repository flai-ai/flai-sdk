import unittest
from unittest import mock

from flai_sdk.api.client import Client
from flai_sdk.config import Config
from flai_sdk.models.cortex import FlowExecutionLogBatch, FlowExecutionLogEntry


class FlowExecutionLogModelsTests(unittest.TestCase):

    def test_batch_dict_drops_none_and_keeps_order(self):
        batch = FlowExecutionLogBatch(logs=[
            FlowExecutionLogEntry(timestamp='2026-07-21T10:00:00Z', level='info',
                                  service_name='flai_cortex.engine', message='{"event": "job.started"}'),
            FlowExecutionLogEntry(level='debug', message='{"event": "node.started"}',
                                  flow_node_execution_id='0be4a5e6-16a0-4907-be3b-745cf6485a17'),
        ])

        body = batch.dict(exclude_none=True)

        self.assertEqual(['logs'], list(body.keys()))
        self.assertEqual(2, len(body['logs']))
        self.assertEqual('{"event": "job.started"}', body['logs'][0]['message'])
        self.assertNotIn('flow_node_execution_id', body['logs'][0])
        self.assertEqual('0be4a5e6-16a0-4907-be3b-745cf6485a17', body['logs'][1]['flow_node_execution_id'])
        self.assertNotIn('timestamp', body['logs'][1])


class PostOnceTests(unittest.TestCase):

    def test_post_once_single_attempt_with_timeout(self):
        config = Config()
        config.flai_access_token = 'token'
        client = Client(config)

        response = mock.Mock(status_code=200, text='{"stored": 1}')
        with mock.patch('flai_sdk.api.client.requests.request', return_value=response) as request:
            body = client.post_once('https://api.test/logs', json={'logs': []})

        self.assertEqual('{"stored": 1}', body)
        self.assertEqual(1, request.call_count)
        self.assertEqual((5, 15), request.call_args.kwargs['timeout'])

    def test_post_once_does_not_retry_on_error(self):
        config = Config()
        config.flai_access_token = 'token'
        client = Client(config)

        response = mock.Mock(status_code=503, text='unavailable')
        with mock.patch('flai_sdk.api.client.requests.request', return_value=response) as request:
            with self.assertRaises(Exception):
                client.post_once('https://api.test/logs', json={'logs': []})

        self.assertEqual(1, request.call_count)


if __name__ == '__main__':
    unittest.main()
