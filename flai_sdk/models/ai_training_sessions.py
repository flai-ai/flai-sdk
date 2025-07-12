from flai_sdk.models.base import BaseModel


class CliAiTrainingSession(BaseModel):

    def __init__(self, name: str, input_ai_model_id: str,
                 training_dataset_id: str, validation_dataset_id: str,
                 learning_rate: float, subsampling: float, in_radius: float,
                 epochs: int, batch_limit: int, train_from_null: bool = None,
                 wandb_id: str = None, wandb_url: str = None, output_semantic_definition_schema_id: str = None):

        self.name = name
        self.input_ai_model_id = input_ai_model_id
        self.training_dataset_id = training_dataset_id
        self.validation_dataset_id = validation_dataset_id
        self.learning_rate = learning_rate
        self.subsampling = subsampling
        self.in_radius = in_radius
        self.epochs = epochs
        self.batch_limit = batch_limit
        self.train_from_null = train_from_null
        self.wandb_id = wandb_id
        self.wandb_url = wandb_url
        self.output_semantic_definition_schema_id = output_semantic_definition_schema_id


class CliAiTrainingSessionPatch(BaseModel):

    def __init__(self, name: str = None, input_ai_model_id: str = None, flow_execution_id: str = None,
                 training_dataset_id: str = None, validation_dataset_id: str = None, output_ai_model_id: str = None,
                 learning_rate: float = None, subsampling: float = None, in_radius: float = None,
                 epochs: int = None, batch_limit: int = None, train_from_null: bool = None,
                 wandb_id: str = None, wandb_url: str = None, status: str = None):

        self.name = name
        self.input_ai_model_id = input_ai_model_id
        self.output_ai_model_id = output_ai_model_id
        self.training_dataset_id = training_dataset_id
        self.validation_dataset_id = validation_dataset_id
        self.learning_rate = learning_rate
        self.subsampling = subsampling
        self.in_radius = in_radius
        self.epochs = epochs
        self.batch_limit = batch_limit
        self.train_from_null = train_from_null
        self.wandb_id = wandb_id
        self.wandb_url = wandb_url
        self.status = status
        self.flow_execution_id = flow_execution_id


class AiTrainingSessionStatusUpdate(BaseModel):

    def __init__(self, flow_execution_id: str,  node_response: dict,
                 flow_id: str = None, node_id: str = None, updated_at: str = None,
                 ):

        self.flow_id = flow_id
        self.node_id = node_id
        self.flow_execution_id = flow_execution_id
        self.node_response = node_response
        self.updated_at = updated_at