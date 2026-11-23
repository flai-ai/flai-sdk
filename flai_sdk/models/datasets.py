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
                 to_organization_id: str = None, skip_preprocessing: bool = None,
                 delete_at: str = None):

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
        self.skip_preprocessing = skip_preprocessing
        self.delete_at = delete_at

class LocalDataset(BaseModel):

    def __init__(self, dataset_name: str = None, description: str = None, unit: str = None,
                 semantic_definition_schema_id: str = None,):

        self.dataset_name = dataset_name
        self.description = description
        self.unit = unit
        self.semantic_definition_schema_id = semantic_definition_schema_id


class LocalHostedPointcloud(BaseModel):
    """One COPC tile in a `LocalHostedDataset`.

    `path` is the tile's filename under the dataset's `copc/` folder; `extent_3d` is
    [minx, miny, minz, maxx, maxy, maxz] and flai-be requires all six values.
    """

    def __init__(self, filename: str = None, path: str = None, point_count: int = None,
                 extent_3d: list = None):

        self.filename = filename
        self.path = path
        self.point_count = point_count
        self.extent_3d = extent_3d


class LocalHostedDataset(BaseModel):
    """Body for `POST /organization/{id}/datasets/local-hosted`, sent by cortex's `flai view`.

    Metadata only - filenames, extents, point counts, CRS. No point data is uploaded, which
    is the point: the tiles are served to the browser from a loopback server on the caller's
    own machine, so LAS never reaches Flai storage. That is why there is no import datasource
    and no upload key here.

    `path` and every `pointclouds[].path` are relative to the cortex DATA_FOLDER, which is also
    the root the caller's loopback server serves - so one string serves both the browser
    (prefixed with `datasource_url`) and cortex (resolved under DATA_FOLDER). flai-be rejects
    absolute paths and `..`.

    Set `dataset_id` to update a dataset registered by an earlier run instead of creating
    another one, and `compute_cluster_id` to let that cluster claim the edit flows for it
    (without one the dataset is view-only).
    """

    def __init__(self, dataset_name: str = None, unit: str = None, path: str = None,
                 datasource_url: str = None, pointclouds: list = None, srid: int = None,
                 description: str = None, overview: str = None, point_count: int = None,
                 compute_cluster_id: str = None, dataset_id: str = None,
                 semantic_definition_schema_id: str = None):

        self.dataset_name = dataset_name
        self.unit = unit
        self.path = path
        self.datasource_url = datasource_url
        self.pointclouds = pointclouds if pointclouds is not None else []
        self.srid = srid
        self.description = description
        self.overview = overview
        self.point_count = point_count
        self.compute_cluster_id = compute_cluster_id
        self.dataset_id = dataset_id
        self.semantic_definition_schema_id = semantic_definition_schema_id
