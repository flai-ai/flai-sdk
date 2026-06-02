#!/usr/bin/env python
import os, json, time, click, uuid, datetime
from typing     import Any, Callable, TypeVar
from glob       import glob
from functools  import wraps
from pathlib    import Path
from tempfile   import NamedTemporaryFile
from contextlib import contextmanager
from typing     import Optional


from flai_sdk                import config, utils
from flai_sdk.api            import datasets        as datasets_api, \
                                    project_dataset as project_dataset_api,\
                                    downloads       as downloads_api, \
                                    organizations   as organizations_api, \
                                    cli_clients     as cli_clients_api, \
                                    cli_executions  as cli_executions_api,\
                                    ai_models       as ai_models_api, \
                                    login           as login_api
from flai_sdk.models         import datasets, project_dataset, cli_clients, cli_executions, ai_models
from flai_sdk.tools          import fileinfo as fi
from flai_sdk.tools.download import download_prepared_zip, define_download_target



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
@click.option("--profile", default=None, envvar="FLAI_PROFILE",
              help="Config profile name. Reads ~/.flai.<profile> instead of ~/.flai (e.g. --profile local)")
@click.pass_context
def cli(ctx, profile):
    if profile:
        config.Config.config_filepath = Path.home() / f'.flai.{profile}'
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())



def _remove_stale_lock(lock_path: Path, max_age: Optional[float] = 600.0) -> bool:
    """
    remove lock_path iff it's stale.
    staleness rules:
    - if the file embeds 'pid=...' and 'ts=...' (your lock writer does), then:
        • if max_age is set and now - ts > max_age -> stale
        • on POSIX, if the PID no longer exists -> stale
    - if metadata can't be parsed, fall back to mtime/max_age (if provided).
    returns True if the lock file was removed (or didn't exist), False if it was kept.
    """
    lock_path = Path(lock_path)
    if not lock_path.exists():
        return True

    pid = None
    ts = None
    try:
        with lock_path.open("r", encoding="utf-8") as f:
            txt = f.read()
        # very simple parser for lines like: "pid=1234 ts=1693320000.0\n"
        parts = dict(kv.split("=", 1) for kv in txt.replace("\n", " ").split() if "=" in kv)
        if "pid" in parts:
            pid = int(parts["pid"])
        if "ts" in parts:
            ts = float(parts["ts"])
    except Exception:
        pass  # keep pid/ts as None

    # helper: POSIX pid check
    def _pid_alive(p: int) -> bool:
        if p is None or p <= 0:
            return False
        if os.name == "posix":
            try:
                os.kill(p, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True   # running but not our process
            else:
                return True
        # on Windows w/o psutil, skip PID probing; rely on age instead.
        return True

    now = time.time()
    age = None
    if ts is not None:
        age = max(0.0, now - ts)
    else:
        try:
            age = max(0.0, now - lock_path.stat().st_mtime)
        except OSError:
            age = None

    stale = False
    if max_age is not None and age is not None and age > max_age:
        stale = True
    elif pid is not None and os.name == "posix" and not _pid_alive(pid):
        stale = True

    if stale:
        try:
            os.unlink(lock_path)
            return True
        except FileNotFoundError:
            return True  # someone else removed it
        except OSError:
            return False  # couldn't remove; keep it

    return False


@contextmanager
def file_lock(lock_path: Path,
            timeout: float = 10.0,
            poll: float = 0.1,
            break_stale_after: Optional[float] = 600.0):
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            # Try to clear a stale lock (best-effort)
            if break_stale_after is not None:
                _remove_stale_lock(lock_path, max_age=break_stale_after)
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out acquiring file lock: {lock_path}")
            time.sleep(poll)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()} ts={time.time()}\n")
        yield
    finally:
        try:
            os.unlink(lock_path)
        except FileNotFoundError:
            pass


def backup_current(target: Path, timestamp_str: str) -> Optional[Path]:
    """
    if target exists, create an atomic backup file with the exact bytes.
    returns the backup path or None.
    """
    if not target.exists():
        return None

    # avoid ':' (illegal on Windows); format: YYYY-MM-DD_HH-MM-SS
    safe_ts = timestamp_str.replace(":", "-")
    backup_path = target.parent / f"{target.name}.{safe_ts}.backup"

    try:
        with target.open("rb") as rf:
            data = rf.read()
    except OSError:
        return None  # unreadable → skip backup (we still proceed with write)

    # make copy
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("wb", dir=str(target.parent), delete=False) as tf:
        tf.write(data)
        tmp_name = tf.name

    # limit permissions
    try:
        os.chmod(tmp_name, 0o600)
    except Exception:
        pass

    # atomic replace
    os.replace(tmp_name, backup_path)


@cli.command(context_settings=CONTEXT, help="Login to Flai.")
@click.option("-nb", "--no-browser", is_flag=True, help="Use this if you're on a headless server or cannot open a browser.")
@display_error
def login(no_browser: bool) -> None:
    flai_login = login_api.FlaiLogin()
    lock_timeout_in_seconds = 10

    # capture timestamp *before* requesting the token (Windows-safe format (no colons))
    backup_timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())

    # wait for generated token
    was_token_generated = flai_login.send_request_for_temporary_token_and_wait_for_real_token(
        open_browser=not no_browser
    )

    if was_token_generated:
        generated_token = flai_login.get_useable_token()
        
        target = Path.home() / Path('.flai')

        # simple lock next to the file to avoid clobbering in concurrent runs.
        lock_path = target.parent / (target.name + ".lock")

        with file_lock(lock_path, timeout=lock_timeout_in_seconds):
            tmp_config = config.Config()

            # we set generic values if file does not exist; should be { 'flai_host': 'https://api.flai.ai' }
            payload = {
                next((param for param in tmp_config.get_params() if "host" in param), 'flai_host'): tmp_config.flai_host
            }

            # read existing JSON if present; tolerate empty/bad JSON by starting fresh.
            if target.exists():
                backup_current(target, backup_timestamp)

                try:
                    with target.open("r", encoding="utf-8") as fh:
                        loaded = json.load(fh)
                        if isinstance(loaded, dict):
                            payload = loaded    # using payload = {} before this line should not be necessary since loaded will overwrite everything if some of the data exist
                except (json.JSONDecodeError, OSError):
                    pass

            # update only token_id
            payload[next((param for param in tmp_config.get_params() if "token" in param), 'flai_access_token')] = generated_token

            # atomic write; write to a temp file in the same directory, then os.replace().
            target.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile("w", encoding="utf-8", dir=str(target.parent), delete=False) as tf:
                json.dump(payload, tf, indent=2, ensure_ascii=False)
                tmp_name = tf.name

            # 0600 perms recommended for secrets
            try:
                os.chmod(tmp_name, 0o600)
            except Exception:
                pass

            os.replace(tmp_name, target)  # atomic on same filesystem

        print(f' Login was successful :D\n')
    
    else:
        print(f' Login failed, token could not be obtained. Please try again.\n')


@cli.command(context_settings=CONTEXT, help="Upload dataset to WebApp.", no_args_is_help=True)
@click.argument("path_to_files")
@click.option("-p", "--project_id", default=None, help="If you would like to associate the dataset with project")
@click.option("-n", "--dataset_name", default=None, help="Name of dataset (If None current timestamp will be used)")
@click.option("-t", "--dataset_type_key", default='pointcloud', help="Dataset type key (pointcloud, vector, raster, image)")
@click.option("-s", "--srid", default="3857", help="SRID value. [default: 3857]")
@click.option("-u", "--unit", default="m", help="Unit value (possible values are m, ft, us-ft, deg) [default: m]")
@click.option("-l", "--semantic_definition_schema_id", default='12e72edc-811d-4677-8bb4-67eaf0e53fc5',
              help="Semantic definition schema ID that already exists on Flai WebApp.")
@click.option("--skip-preprocessing", is_flag=True, default=False,
              help="Skip server-side preprocessing. Requires pre-computed COPC files and overview.copc.laz.")
@click.option("--preprocess", is_flag=True, default=False,
              help="Preprocess locally: convert to COPC, generate overview, compute stats. Requires pdal CLI.")
@click.option("--delete-at", default=None,
              help="Auto-delete dataset at this date (ISO format, e.g. 2026-04-01).")
@display_error
def upload_dataset(path_to_files, project_id, dataset_name, dataset_type_key, srid, unit, semantic_definition_schema_id, skip_preprocessing, preprocess, delete_at, **params: Any) -> None:

    if unit not in ['m', 'ft', 'us-ft', 'deg']:
        click.echo(f'Given unit "{unit}" not supported. Quiting upload.', color='red')
        return

    try:
        uuid.UUID(semantic_definition_schema_id, version=4)
    except ValueError:
        click.echo(f'Given semantic definition schema ID "{semantic_definition_schema_id}" is not a valid UUID. Quiting upload.', color='red')
        return

    path_input = Path(path_to_files)
    if path_input.is_absolute():
        files = list(path_input.parent.glob(path_input.name))
    else:
        files = list(Path.cwd().glob(path_to_files))
    is_temp_file = False
    flai_config = config.Config()
    organization = organizations_api.FlaiOrganization()
    org_name_adress = organization.get_organization_name_and_address()
    to_organization_id = organization.get_active_organization()

    if len(files) == 0:
        click.echo(f'No files at given path {path_to_files}. Quiting...', color='red')
        return

    flai_dataset = datasets_api.FlaiDataset()
    if dataset_name is None:
        dataset_name = f'Flai SDK {path_to_files.parents[0]} {datetime.datetime.now()}'

    click.echo(
        f'Files from {path_to_files} will be uploaded as new dataset "{dataset_name}" to {flai_config.get_web_app_url()}')

    click.echo(f'Uploading dataset to organization: {org_name_adress}...')

    # Local preprocessing: convert to COPC, generate overview, compute stats
    if preprocess:
        import tempfile as tmpmod
        from flai_sdk.tools.copc_preprocessor import CopcPreprocessor

        with tmpmod.TemporaryDirectory() as tmp_dir:
            preprocessor = CopcPreprocessor(
                input_files=files,
                output_dir=Path(tmp_dir),
                unit=unit,
                log_fn=click.echo,
            )
            zip_path, dataset_stats, file_stats = preprocessor.run()

            new_dataset = flai_dataset.upload_precomputed_copc(
                datasets.Dataset(dataset_name=dataset_name, dataset_type_key=dataset_type_key,
                                 srid=srid, unit=unit, semantic_definition_schema_id=semantic_definition_schema_id,
                                 to_organization_id=to_organization_id, delete_at=delete_at),
                zip_path,
                dataset_stats=dataset_stats,
                file_stats=file_stats,
            )
    else:
        if len(files) > 1:
            click.echo('More then one file found. Zipping...')
            path_to_files = Path(path_to_files)
            temp_filename = str(uuid.uuid4())
            import_file = utils.zip_all_files(path_to_files.parents[0], path_to_files.name, temp_filename)
            is_temp_file = True
        else:
            import_file = files[0]

        new_dataset = flai_dataset.upload_and_post_datasets(
            datasets.Dataset(dataset_name=dataset_name, dataset_type_key=dataset_type_key,
                             srid=srid, unit=unit, semantic_definition_schema_id=semantic_definition_schema_id,
                             to_organization_id=to_organization_id,
                             skip_preprocessing=skip_preprocessing if skip_preprocessing else None,
                             delete_at=delete_at),
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

    if is_temp_file and not preprocess:
        import_file.unlink()

    click.echo(f'\nDone', color='green')


@cli.command(context_settings=CONTEXT, help="Uploading AI model to WebApp.", no_args_is_help=True)
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

    ai_model_extensions = ['.yaml', '.pth', '.py', '.tar', '.pickle', '.txt', '.flenc']
    files = glob(os.path.join(path_to_folder, '*'))
    files = [f for f in files if os.path.splitext(f)[1] in ai_model_extensions]

    if len(files) == 0:
        click.echo(f'No suitable files at given path {path_to_folder}. Quiting...', color='red')
        return

    flai_config = config.Config()
    organization = organizations_api.FlaiOrganization()
    org_name_address = organization.get_organization_name_and_address()

    if len(files) > 1:
        click.echo('More than one file found. Zipping them before upload.')
    else:
        click.echo('One file found. Zipping it before upload.')
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


@cli.command(context_settings=CONTEXT, help="List all CLI clients.")
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



@cli.command(context_settings=CONTEXT, help="Download dataset from WebApp.", no_args_is_help=True)
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


@cli.command(context_settings=CONTEXT, help="Download FlaiNet AI model from WebApp.", no_args_is_help=True)
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


@cli.command(context_settings=CONTEXT, help="Prints info about file.", no_args_is_help=True)
@click.argument("file_path")
@display_error
def fileinfo(file_path, **params: Any) -> None:
    click.echo(f'Looking at file {file_path}')

    file = Path(file_path)

    if not file.exists():
        click.echo(f'File {file_path} not found')

    fi.fileinfo(file)
    click.echo(f'\nDone', color='green')


@cli.command(context_settings=CONTEXT, help="Converts units from Feet To Meter.", no_args_is_help=True)
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
