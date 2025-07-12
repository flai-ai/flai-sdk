#!/usr/bin/env python
from typing import Any, Callable, TypeVar
import os
import random
from glob import glob
from functools import wraps
import click
from pathlib import Path
import uuid
import datetime
from flai_sdk import config
from flai_sdk.api import datasets as datasets_api, projects as project_api, project_dataset as project_dataset_api,\
    downloads as downloads_api, organizations as organizations_api, cli_clients as cli_clients_api, \
    cli_executions as cli_executions_api,  ai_models as ai_models_api
from flai_sdk.models import datasets, projects, project_dataset, cli_clients, cli_executions, ai_models
from flai_sdk.tools import fileinfo as fi
from flai_sdk.tools.download import download_prepared_zip, define_download_target

from flai_sdk import utils

FC = TypeVar("FC", bound=Callable[..., Any])

CONTEXT = dict(default_map={})


def display_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise e

    return wrapper


class RunGroup(click.Group):
    @display_error
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        return None


@click.command(cls=RunGroup, invoke_without_command=True)
# @click.version_option(version=flai_sdk._version)
@click.pass_context
def cli(ctx):
    # wandb.try_to_set_up_global_logging()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command(context_settings=CONTEXT, help="Login to Flai")
@display_error
def login(**params: Any) -> None:
    flai_config = config.Config()

    for param in flai_config.get_params():
        value = click.prompt(f"Please enter {param.lower()}", default=getattr(flai_config, param))
        setattr(flai_config, param, value)

    for param in flai_config.get_params():
        click.echo(f"The value of parameter '{param}' was set to {getattr(flai_config, param)}")

    flai_config.save()
    click.echo('\nSaved')


@cli.command(context_settings=CONTEXT, help="Upload dataset to WebApp")
@click.argument("path_to_files")
@click.option("-p", "--project_id", default=None, help="If you would like to associate the dataset with project")
@click.option("-n", "--dataset_name", default=None, help="Name of dataset (If None current timestamp will be used)")
@click.option("-t", "--dataset_type_key", default='pointcloud', help="Dataset type key (pointcloud, vector, raster, image)")
@click.option("-s", "--srid", default="3857", help="SRID value. [default: 3857]")
@click.option("-u", "--unit", default="m", help="Unit value (possible values are m, ft, us-ft, deg) [default: m]")
@click.option("-l", "--semantic_definition_schema_id", default='12e72edc-811d-4677-8bb4-67eaf0e53fc5',
              help="Semantic definition schema ID that already exists on Flai WebApp.")
@display_error
def upload_dataset(path_to_files, project_id, dataset_name, dataset_type_key, srid, unit, semantic_definition_schema_id, **params: Any) -> None:

    if unit not in ['m', 'ft', 'us-ft', 'deg']:
        click.echo(f'Given unit "{unit}" not supported. Quiting upload.', color='red')
        return

    try:
        uuid.UUID(semantic_definition_schema_id, version=4)
    except ValueError:
        click.echo(f'Given semantic definition schema ID "{semantic_definition_schema_id}" is not a valid UUID. Quiting upload.', color='red')
        return

    files = list(Path.cwd().glob(path_to_files))
    is_temp_file = False
    flai_config = config.Config()
    organization = organizations_api.FlaiOrganization()
    org_name_adress = organization.get_organization_name_and_address()
    to_organization_id = organization.get_active_organization()

    if len(files) == 0:
        click.echo(f'No files at given path {path_to_files}. Quiting...', color='red')
        return

    elif len(files) > 1:
        click.echo('More then one file found. Zipping...')
        path_to_files = Path(path_to_files)
        temp_filename = str(uuid.uuid4())
        import_file = utils.zip_all_files(path_to_files.parents[0], path_to_files.name, temp_filename)
        is_temp_file = True
    else:
        import_file = files[0]

    flai_dataset = datasets_api.FlaiDataset()
    if dataset_name is None:
        dataset_name = f'Flai SDK {path_to_files.parents[0]} {datetime.datetime.now()}'

    click.echo(
        f'Files from {path_to_files} will be uploaded as new dataset "{dataset_name}" to {flai_config.get_web_app_url()}')

    click.echo(f'Uploading dataset to organization: {org_name_adress}...')

    new_dataset = flai_dataset.upload_and_post_datasets(
        datasets.Dataset(dataset_name=dataset_name, dataset_type_key=dataset_type_key,
                         srid=srid, unit=unit, semantic_definition_schema_id=semantic_definition_schema_id,
                         to_organization_id=to_organization_id),
        import_file)

    dataset_id = new_dataset['id']
    click.echo(
        f'\nDataset successfully uploaded: {flai_config.get_web_app_url()}#/admin/pages:catalogue/{dataset_id}/show')

    if project_id is not None:
        flai_project_dataset = project_dataset_api.FlaiProjectDataset()
        flai_project_dataset.post_project_dataset(
            project_dataset=project_dataset.ProjectDataset(project_id=project_id, dataset_id=dataset_id))
        click.echo(
            f'Dataset attached to the project: {flai_config.get_web_app_url()}#/admin/pages:projects/{project_id}/show')

    if is_temp_file:
        import_file.unlink()

    click.echo(f'\nDone', color='green')


@cli.command(context_settings=CONTEXT, help="Uploading AI model to WebApp")
@click.argument("path_to_folder")
@click.option("-n", "--model_name", default=None, required=True,
              help="Name of the uploaded model.")
@click.option("-d", "--description", default=None, required=True,
              help="Describes the model.")
@click.option("-t", "--dataset_type_key", default='pointcloud', required=False,
              help="Model input and output dataset type key (pointcloud, vector, raster, image).")
@click.option("-m", "--model_type_key", default='pointcloud', required=False,
              help="Model type (e.g. semantic segmentation, panoptic, classification).")
@click.option("-l", "--semantic_definition_schema_id", default=None, required=True,
              help="Semantic definition schema ID that already exists on Flai WebApp.")
@click.option("-f", "--framework", default='Torch', required=False,
              help="Framework used for training the model.")
@click.option("-p", "--public", is_flag=True, show_default=True, default=False,
              help="If enabled, uploaded model will be seen to everyone.")
@click.option("-t", "--trainable", is_flag=True, show_default=True, default=False,
              help="If enabled, uploaded model can be used in retraining process.")
@display_error
def upload_ai_model(path_to_folder, model_name, description, dataset_type_key, model_type_key, semantic_definition_schema_id, framework, public, trainable, **params: Any) -> None:

    if dataset_type_key not in ['pointcloud', 'vector', 'raster', 'image']:
        click.echo(f'Given dataset type "{dataset_type_key}" not supported. Quiting upload.', color='red')
        return

    if not os.path.isdir(path_to_folder):
        click.echo(f'Given path "{path_to_folder}" is not a folder. Quiting upload.', color='red')
        return

    try:
        uuid.UUID(semantic_definition_schema_id, version=4)
    except ValueError:
        click.echo(f'Given semantic definition schema ID "{semantic_definition_schema_id}" is not a valid UUID. Quiting upload.', color='red')
        return

    if description == "":
        description = "Not provided."

    ai_model_extensions = ['.yaml', '.pth', '.py', '.tar', '.pickle', '.txt']
    files = glob(os.path.join(path_to_folder, '*'))
    files = [f for f in files if os.path.splitext(f)[1] in ai_model_extensions]

    if len(files) == 0:
        click.echo(f'No suitable files at given path {path_to_folder}. Quiting...', color='red')
        return

    flai_config = config.Config()
    organization = organizations_api.FlaiOrganization()
    org_name_address = organization.get_organization_name_and_address()

    click.echo('More then one file found. Zipping them before upload.')
    path_to_files = Path(path_to_folder)
    temp_filename = str(uuid.uuid4())
    import_file = utils.zip_all_file_in_list(path_to_files.parents[0], files, temp_filename)

    click.echo(f'Uploading AI model to organization: {org_name_address}...')
    click.echo(f'Files ({len(files)}) from {path_to_folder} will be uploaded as AI model "{model_name}" to {flai_config.get_web_app_url()}')

    flai_ai_model = ai_models_api.FlaiAiModel()
    new_ai_model = flai_ai_model.upload_ai_model(
        ai_models.AiModel(title=model_name, description=description, framework=framework,
                          input_dataset_type_key=dataset_type_key, output_dataset_type_key=dataset_type_key,
                          is_public=public, is_trainable=trainable, ai_model_type=model_type_key,
                          semantic_definition_schema_id=semantic_definition_schema_id),
        import_file)

    click.echo(f'\nAI model successfully uploaded: {flai_config.get_web_app_url()}#/admin/pages:ai-models/{new_ai_model["id"]}/show')

    import_file.unlink()

    click.echo(f'\nDone', color='green')


@cli.command(context_settings=CONTEXT, help="List all CLI clients")
@display_error
def get_cli_clients(**params: Any) -> None:

    click.echo(f'Preparing files for download, please wait...')
    flai_config = config.Config()
    base_url = flai_config.flai_host.rstrip("/")

    # Get all clients (NO NEED TO DO THIS IN AI-CLI)
    clients_api = cli_clients_api.FlaiCliClient()
    clients = clients_api.get_cli_clients()
    print(clients)

    # First time create new CLI-Client and store ID to ~/.flai
    client = clients_api.post_cli_client(cli_client=cli_clients.CliClient(
        fingerprint='neki-hash-talk-with-@andreh',
        mac_address='sdjalfksadjl',
        metadata='{"Json Meta data about your machine": "gpurtx3030"}'
    ))

    # Backend will check if this client has permission ETC... Now we can create CLI Flow execution
    client_id = client['id']
    flow_id = "ac83b680-5bce-4845-9509-2d087399c1ae"
    print(f'Running flow with id {flow_id} on client : {client["id"]}')

    cli_exec_api = cli_executions_api.FlaiCliExecutions()

    execution = cli_exec_api.post_cli_execution(client_id=client_id, cli_execution=cli_executions.CliExecution(
        flow_id=flow_id,
        status="processing",
    ))
    # This one also returns the whole flow you will need for execution
    cli_execution_id = execution['id']

    # To update at each not just call patch with payload (PHP will propagate to flow node execution and billings)
    execution = cli_exec_api.patch_cli_execution(client_id=client_id, cli_execution_id=cli_execution_id, cli_execution=cli_executions.CliExecution(
        node_completed_payload={
            "payload": {
                "flow_id": "6f45a853-fb44-4847-b4c9-f18fa3c90d96",
                "flow_execution_id": "1759a703-7eab-4e8a-b813-1ed1c267b2bc",
                "status": True,
                "started_at": "2023-08-04 00:00:00",
                "finished_at": "2023-08-05 00:00:00",
                "execution_time": 10,
                "node_settings": {
                    "options": {
                        "dataset_id": "null"
                    },
                    "flow_node_definition_id": "6e12437d-f316-4006-8690-b445a56dc448",
                    "flow_node_execution_id": "1b3e68a2-9eb8-4c20-90b8-e01fa093a4f6",
                    "type": "reader"
                },
                "billing": {
                    "runtime_environment": "local",
                    "values": [
                        {
                            "resource": "area_km2",
                            "value": 10
                        },
                        {
                            "resource": "compute_point_count",
                            "value": 100
                        }
                    ]
                }
                }
            }
    ))



@cli.command(context_settings=CONTEXT, help="Download dataset from WebApp")
@click.argument("path_to_output")
@click.option("-d", "--dataset_id", default=None, help="ID of the dataset")
@display_error
def download_dataset(path_to_output: str, dataset_id: str, **params: Any) -> None:

    click.echo(f'Preparing files for download, please wait...')
    save_path = define_download_target(path_to_output, dataset_id)

    flai_config = config.Config()
    base_url = flai_config.flai_host.rstrip("/")

    flai_download = downloads_api.FlaiDownload()
    download_id = flai_download.post_download(dataset_id, 'datasets')['id']

    download_complete = download_prepared_zip(click, base_url, save_path, download_id)
    if download_complete:
        click.echo(f'\nDone', color='green')
    else:
        click.echo(f'\nDownload failes', color='red')


@cli.command(context_settings=CONTEXT, help="Download FlaiNet AI model from WebApp")
@click.argument("path_to_output")
@click.option("-m", "--model_id", default=None, help="ID of the model")
@display_error
def download_flainet_model(path_to_output: str, model_id: str, **params: Any) -> None:

    save_path = define_download_target(path_to_output, model_id)

    flai_config = config.Config()
    base_url = flai_config.flai_host.rstrip("/")

    model_organization_id = ai_models_api.FlaiAiModel().get_stored_in_organization(model_id)
    if model_organization_id is None:
        click.echo(f'Unknown Ai model. Download stopped.', color='red')
        return

    click.echo(f'Preparing files for download, please wait...')

    flai_download = downloads_api.FlaiDownload()
    download_id = flai_download.post_download(model_id, 'ai_models', active_org_id=model_organization_id)['id']

    download_complete = download_prepared_zip(click, base_url, save_path, download_id)
    if download_complete:
        click.echo(f'\nDone', color='green')
    else:
        click.echo(f'\nDownload failes', color='red')


@cli.command(context_settings=CONTEXT, help="Prints info about file")
@click.argument("file_path")
@display_error
def fileinfo(file_path, **params: Any) -> None:
    click.echo(f'Looking at file {file_path}')

    file = Path(file_path)

    if not file.exists():
        click.echo(f'File {file_path} not found')

    fi.fileinfo(file)
    click.echo(f'\nDone', color='green')


@cli.command(context_settings=CONTEXT, help="Converts units from Feet To mMeter")
@click.argument("file_in")
@click.argument("file_out")
@display_error
def convert_feet_meter(file_in, file_out, **params: Any) -> None:
    click.echo(f'Converting {file_in}')

    file_in = Path(file_in)

    if not file_in.exists():
        click.echo(f'File {file_in} not found')

    fi.convertFeetToMeters(file_in, Path(file_out))
    click.echo(f'Saved as {file_out}')
    click.echo(f'\nDone', color='green')

