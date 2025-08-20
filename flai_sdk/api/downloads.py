from .base import FlaiService
import json


class FlaiDownload(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}/downloads'

    def post_download(self, id: str, data_type: str, active_org_id: str = None) -> list:
        data_dict = {"items": [{"model_name": data_type, "model_id": id}]}
        if active_org_id is not None:
            return json.loads(self.client.post(f'{self._get_service_url(self.base_url, active_org_id=active_org_id)}', json=data_dict))
        else:
            return json.loads(self.client.post(f'{self.service_url}', json=data_dict))

    def get_download(self, download_id):
        return self.client.get(f'{self.service_url}/{download_id}?decorators=files')

    def download_file(self, url):
        return self.client.get_content(url)
