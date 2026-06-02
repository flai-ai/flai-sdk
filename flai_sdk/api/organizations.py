from .base import FlaiService


class FlaiOrganization(FlaiService):

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}/organizations'

    def _get_me(self):
        return self.client.get(f'{"/".join(self.service_url.split("/")[:-1])}/oauth/me')

    def get_active_organization(self):
        return self._get_me()['active_organization_id']

    def get_organization_name_and_address(self):
        data = self._get_me()
        return f'"{data["organization"]["name"]}, {data["organization"]["address"]}"'

    def is_super_admin(self):
        return 'super-admin' in self._get_me()['user_permissions']

    def get_organizations(self):
        return self.client.get(self.service_url)
