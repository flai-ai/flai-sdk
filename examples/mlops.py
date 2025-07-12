from flai.api import datasets as datasets_api, projects as project_api, project_dataset as project_dataset_api
from flai.models import datasets, projects, project_dataset
from pathlib import Path

project_name = 'My MLOPS Test project'
project_id = '5e987ba4-447a-482a-a821-00a68bcacfc5'

# Check if project exists
flai_project = project_api.FlaiProject()
project = flai_project.get_project(project_id)

# Create new project
new_project = flai_project.post_project(projects.Project(name=project_name, description='Jej'))

# Create and upload new dataset to the Flai

flai_dataset = datasets_api.FlaiDataset()
new_dataset = flai_dataset.upload_and_post_datasets(
    datasets.Dataset(dataset_name='Test-WANDB_NAME', dataset_type_key='pointcloud',
                     description='[Wandb - project](https://wandb.ai/flai/test-flai-pointai-labs/runs/2a15hqoh?workspace=user-flai)'),
    Path('./examples/wt.zip'))

print(new_project, new_dataset)

# Attach Dataset to Project
flai_project_dataset = project_dataset_api.FlaiProjectDataset()
flai_project_dataset.post_project_dataset(
    project_dataset=project_dataset.ProjectDataset(project_id=new_project['id'], dataset_id=new_dataset['id']))


# TODO Upload AI Model
