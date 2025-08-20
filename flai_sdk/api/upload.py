from .base import FlaiService
from pathlib import Path
import uuid
import os
import json


class FlaiUpload(FlaiService):
    MIN_CHUNK_INDEX: int = 10000  # for easier sorting on BE
    DEFAULT_CHUNK_SIZE: int = 8000000  # 8mb

    session_id: str = None

    @staticmethod
    def _get_service_url(base_url: str, active_org_id: str = None) -> str:
        return f"{base_url}/tools/upload"

    @staticmethod
    def _read_in_chunks(file_object, chunk_size=DEFAULT_CHUNK_SIZE):
        while True:
            data = file_object.read(chunk_size)
            if not data:
                break
            yield data

    def upload_file(self, filepath: Path, dataset_type_key: str) -> dict:

        if not filepath.is_file():
            raise FileNotFoundError(filepath)

        self.session_id = str(uuid.uuid4())
        content_size = os.stat(filepath).st_size

        with open(filepath, 'rb') as f:

            chunk_index = self.MIN_CHUNK_INDEX
            offset = self.DEFAULT_CHUNK_SIZE
            chunk_start_byte = 0
            headers = {}

            payload = {
                "file_name": filepath.name,
                "total_file_size": content_size,
                "session_key": self.session_id,
                "dataset_type": dataset_type_key
            }

            for n, file_chunk in enumerate(self._read_in_chunks(f)):
                chunk_end_byte = chunk_start_byte + len(file_chunk)
                payload['chunk_start_byte'] = chunk_start_byte
                payload['chunk_end_byte'] = chunk_end_byte
                payload['chunk_index'] = self.MIN_CHUNK_INDEX + n

                files = [('file_chunk', (filepath.name, file_chunk, 'application/octet-stream'))]
                try:
                    response = self.client.post(self.service_url, data=payload, files=files)
                except Exception as e:
                    print(e)
                chunk_start_byte += offset

        return json.loads(response)
