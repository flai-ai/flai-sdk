from .base import FlaiService


class FlaiOrganization(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organizations'

    def get_active_organization(self):
        data = self.client.get(f'{"/".join(self.service_url.split("/")[:-1])}/oauth/me')
        return data['active_organization_id']

    def get_organization_name_and_address(self):
        data = self.client.get(f'{"/".join(self.service_url.split("/")[:-1])}/oauth/me')
        return f'"{data["organization"]["name"]}, {data["organization"]["address"]}"'

    def get_organizations(self):
        return self.client.get(self.service_url)
