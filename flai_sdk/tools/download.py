import os
import time
import requests
from flai_sdk.api import downloads as downloads_api
from flai_sdk.api import file_downloads as file_downloads_api


def download_prepared_zip(click, base_url: str, save_path: str, download_id: str) -> bool:
    flai_download = downloads_api.FlaiDownload()
    flai_file_download = file_downloads_api.FlaiFileDownload()

    while True:
        response = flai_download.get_download(download_id)

        if len(response['files']) > 0:
            if click is not None:
                click.echo(f'Source name: "{response["files"][0]["name"]}",'
                           f' size in MB: {round(response["files"][0]["size"] / 10 ** 6, 2)}')

        if response['status'] == 'download-prepared':
            if click is not None:
                click.echo(f'Files are prepared, downloading and saving them to: {save_path}')
            presigned_url = flai_file_download.download(response["files"][0]["id"])

            if presigned_url["url"].startswith('http'):
                download_url = presigned_url["url"]
            else:
                download_url = f'{base_url}/presigned{presigned_url["url"]}'

            download_response = requests.get(download_url, verify=False)
            if download_response.status_code != 200:
                raise Exception(f"Model download failed.")

            with open(save_path, 'wb') as f:
                f.write(download_response.content)

            break

        time.sleep(2)

    return True


def define_download_target(path: str, u_id: str) -> str:
    if os.path.isdir(path):
        save_path = os.path.join(path, f'{u_id}.zip')
    else:
        save_path = f'{path}.zip'
    return save_path
