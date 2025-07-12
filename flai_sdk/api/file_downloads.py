from .base import FlaiService

class FlaiFileDownload(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organization/{active_org_id}/file-downloads'

    def download(self, file_download_id):
        return self.client.get(f'{self.service_url}/{file_download_id}/download')
