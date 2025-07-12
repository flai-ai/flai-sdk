from flai_sdk.models.base import BaseModel
from flai_sdk.models.datasource import Datasource


class AiModel(BaseModel):

    def __init__(self, title: str = None, description: str = None, framework: str = None, version: str = None,
                 input_dataset_type_key: str = None, output_dataset_type_key: str = None, from_train_session: bool = None,
                 is_public: bool = False, is_trainable: bool = False, ai_model_type: str = None,
                 semantic_definition_schema_id: str = None, import_datasource: Datasource = None):

        self.title = title
        self.description = description
        self.framework = framework
        self.version = version
        self.input_dataset_type_key = input_dataset_type_key
        self.output_dataset_type_key = output_dataset_type_key
        self.is_public = is_public
        self.is_trainable = is_trainable
        self.ai_model_type = ai_model_type
        self.semantic_definition_schema_id = semantic_definition_schema_id
        self.import_datasource = import_datasource
        self.from_train_session = from_train_session
