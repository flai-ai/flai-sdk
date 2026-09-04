import logging
import os
import requests
import json as json_lib
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 300.0
# Uploads are read-unbounded on purpose. After the body is sent the server stays silent until it has
# ingested the whole thing, and that silence scales with the data — no fixed figure covers a
# multi-GB point cloud, and aborting a customer's upload part-way is worse than the hang it bounds.
# Connect stays bounded, so an unreachable host still fails fast. Set the env var to impose a limit.
DEFAULT_UPLOAD_READ_TIMEOUT = None


def _env_float(name, default):
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _env_int(name, default):
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default

MAX_ATTEMPTS = _env_int('FLAI_HTTP_MAX_ATTEMPTS', 5)


def _timeout(has_files=False):
    connect = _env_float('FLAI_HTTP_CONNECT_TIMEOUT', DEFAULT_CONNECT_TIMEOUT)
    if has_files:
        return (connect, _env_float('FLAI_HTTP_UPLOAD_READ_TIMEOUT', DEFAULT_UPLOAD_READ_TIMEOUT))
    return (connect, _env_float('FLAI_HTTP_READ_TIMEOUT', DEFAULT_READ_TIMEOUT))


class FlaiApiError(Exception):
    """Exception raised for API errors. Carries the HTTP status code and response body."""

    def __init__(self, status_code, response_body):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"[{status_code}] {response_body}")

    def __reduce__(self):
        return self.__class__, (self.status_code, self.response_body), self.__dict__


def _should_retry(exception):
    """Retry on all exceptions except 4xx API errors (client errors are permanent)."""
    if isinstance(exception, FlaiApiError) and 400 <= exception.status_code < 500:
        return False
    return True


class Client():

    def __init__(self, config):
        self.config = config
        self.token = self.config.flai_access_token

    def _get_headers(self) -> dict:
        return {
            'Accept': 'application/json',
            'Authorization': self._get_authorization()
        }

    def _get_authorization(self):
        return f'Bearer {self.token}'

    @retry(retry=retry_if_exception(_should_retry), stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential_jitter(initial=5, jitter=3))
    def get(self, url, data=None, json=None, skip_check=False):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("GET", url, headers=self._get_headers(), data=data, json=json, files={},
                                    verify=False, timeout=_timeout())
        if not skip_check:
            self.check(response)
        return response.json()

    @retry(retry=retry_if_exception(_should_retry), stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential_jitter(initial=5, jitter=3))
    def get_content(self, url):
        response = requests.request("GET", url, headers=self._get_headers(), data={}, files={}, verify=False,
                                    timeout=_timeout())
        self.check(response)
        return response.content

    @retry(retry=retry_if_exception(_should_retry), stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential_jitter(initial=5, jitter=3))
    def post(self, url, data=None, json=None, files=[]):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("POST", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False, timeout=_timeout(has_files=bool(files)))
        self.check(response)
        return response.text

    def post_once(self, url, data=None, json=None, files=[]):
        """Single-attempt POST for callers that own their retry loop (e.g. the
        cortex log flusher): no tenacity backoff (a 5-attempt exponential wait
        would pin the caller's flush thread for minutes during an outage) and
        explicit timeouts so a hung connection can't block it either. Connect is
        short (unreachable should fail fast; retry is side-effect-free), read is
        longer on purpose: a read timeout after the server already committed the
        batch makes the caller resend it, so impatience here manufactures
        duplicates under exactly the load that makes responses slow."""
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("POST", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False, timeout=(5, 15))
        self.check(response)
        return response.text

    @retry(retry=retry_if_exception(_should_retry), stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential_jitter(initial=5, jitter=3))
    def patch(self, url, data=None, json=None, files=[]):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("PATCH", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False, timeout=_timeout(has_files=bool(files)))
        self.check(response)
        return response.text

    @retry(retry=retry_if_exception(_should_retry), stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential_jitter(initial=5, jitter=3))
    def put(self, url, data=None, json=None, files=[]):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("PUT", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False, timeout=_timeout(has_files=bool(files)))
        self.check(response)
        return response.text

    @staticmethod
    def check(response):

        if not 200 <= response.status_code < 300:
            response_body = Client.parse_response(response)
            LOGGER.warning("flai-be returned HTTP %s for %s", response.status_code,
                           getattr(response, "url", "<unknown url>"))
            LOGGER.debug("flai-be response body: %s", response_body)
            raise FlaiApiError(response.status_code, response_body)

    @staticmethod
    def parse_response(response):
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except (ValueError, json_lib.JSONDecodeError):
            return response.text

    @staticmethod
    def parse_response_from_text(body):
        if body is None or body == '':
            return None
        if isinstance(body, (dict, list)):
            return body
        return json_lib.loads(body)
