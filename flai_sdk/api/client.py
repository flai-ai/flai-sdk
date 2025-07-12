import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


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

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=5, jitter=3))
    def get(self, url, data=None, json=None):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("GET", url, headers=self._get_headers(), data=data, json=json, files={},
                                    verify=False)
        self.check(response)
        return response.json()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=5, jitter=3))
    def get_content(self, url):
        response = requests.request("GET", url, headers=self._get_headers(), data={}, files={}, verify=False)
        self.check(response)
        return response.content

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=5, jitter=3))
    def post(self, url, data=None, json=None, files=[]):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("POST", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False)
        self.check(response)
        return response.text

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=5, jitter=3))
    def patch(self, url, data=None, json=None, files=[]):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("PATCH", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False)
        self.check(response)
        return response.text

    @retry(stop=stop_after_attempt(5), wait=wait_exponential_jitter(initial=5, jitter=3))
    def put(self, url, data=None, json=None, files=[]):
        # TODO remove verify (needed just for debugging on local env)
        response = requests.request("PUT", url, headers=self._get_headers(), json=json, data=data, files=files,
                                    verify=False)
        self.check(response)
        return response.text

    @staticmethod
    def check(response):

        if response.status_code != 200:
            print(f"Response status code {response.status_code}.")
            print(f"Response content {response.json()}.")
            raise Exception(f"{response.json()}")
