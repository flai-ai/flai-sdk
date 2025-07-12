from flai_sdk.models.base import BaseModel
from flai_sdk.models.datasource import Datasource

# copied from FE payload
vector_3d_box_fields_structure = {
    "vector_type": "polygon",
    "vector_dimension": 3,
    "data_table_fields": {
        "attribute_code": {
            "type": "N",
            "size": 3,
            "decimals": 0
        },
        "attribute_name": {
            "type": "C",
            "size": 255,
            "decimals": 0
        },
        "box": {
            "type": "JSON",
            "size": 0,
            "decimals": 0
        }
    }
}


class Dataset(BaseModel):

    def __init__(self, dataset_name: str = None, dataset_type_key: str = None, description: str = None,
                 read_write_mode: str = 'rw', is_public: bool = False, is_annotated: bool = False,
                 import_datasource: Datasource = None, srid: str = None, unit: str = None,
                 vector_dataset: dict = None, semantic_definition_schema_id: str = None,
                 to_organization_id: str = None):

        self.import_datasource = import_datasource
        self.is_annotated = is_annotated
        self.is_public = is_public
        self.read_write_mode = read_write_mode
        self.description = description
        self.dataset_type_key = dataset_type_key
        self.dataset_name = dataset_name
        self.srid = srid
        self.unit = unit
        self.vector_dataset = vector_dataset
        self.semantic_definition_schema_id = semantic_definition_schema_id
        self.to_organization_id = to_organization_id
