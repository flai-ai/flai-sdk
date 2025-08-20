from .base import FlaiPublicService
import json


class FlaiOpenData(FlaiPublicService):
    _bad_status_code = 400


    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f'{base_url}'
    

    def _get_polygon_arg(self, coords: list):
        good_status_code = 200
        headers = {"Content-Type": "application/json"}

        if len(coords) != 4:
            payload = {
                "error": {
                    "code": self._bad_status_code,
                    "message": 'Parameter "geom_filter" should hold 4 values (2 mins and 2 maxs)'
                }
            }
            # Flask interprets this as (body, status, headers)
            return [json.dumps(payload), self._bad_status_code, headers], []
        
        # they probably will not be passed in this order, for ilustration purpose only
        MIN_X, MIN_Y, MAX_X, MAX_Y = coords[0], coords[1], coords[2], coords[3] 
        
        # check if this will work
        final_geom_filter = [
            MIN_X, MIN_Y,
            MIN_X, MAX_Y,
            MAX_X, MIN_Y,
            MAX_X, MAX_Y,
            MIN_X, MIN_Y,
        ]

        geom_param = 'filter[geom]=' + 'gi=' + ','.join(map(str, final_geom_filter))    # gi= is neccessary here
        return [json.dumps({}), good_status_code, headers], geom_param


    def get_possible_region_ids(self, geom_filter: list):
        response, geom_param = self._get_polygon_arg(geom_filter)

        if response[1] == self._bad_status_code:
            return (*response,)

        return self.client.get(f'{self.service_url}/datasets{self.decorators_string}semantic_labels_definition&{geom_param}')


    def get_dataset_files(self, dataset_id: str, geom_filter: list):
        response, geom_param = self._get_polygon_arg(geom_filter)

        if response[1] == self._bad_status_code:
            return (*response,)

        return self.client.get(f'{self.service_url}/datasets/{dataset_id}/pointclouds?{geom_param}')
