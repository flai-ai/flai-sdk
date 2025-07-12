from pathlib import Path
from zipfile import ZipFile
import json
from base64 import b64decode
from Crypto.Cipher import AES
import os


def zip_all_files(path: Path, pattern: str, name:str) -> Path:
    """

    :param path:
    :param pattern:
    :param name:
    :return:
    """

    return zip_all_file_in_list(path, list(Path(path).glob(pattern)), name)


def zip_all_file_in_list(path: Path, files: list, name: str) -> Path:
    """

    :param path:
    :param files:
    :param name:
    :return:
    """
    zipfile_path = f'{path}/{name}.zip'
    with ZipFile(zipfile_path, 'w') as zipObj:
        for file in files:
            zipObj.write(file)

    return Path(zipfile_path)


def decrypt(encrypted_string):
    """Decrypt string

    Args:
        encrypted_string (string)

    Returns:
        string: decrypted string
    """
    unpad = lambda s : s[:-ord(s[len(s)-1:])]
    try:
        key = os.getenv('APP_KEY')
        if key.startswith('base64:'):
            key = key[len('base64:'):]

        enc_json = json.loads(b64decode(encrypted_string).decode('utf-8'))
        cipher = AES.new(b64decode(key), AES.MODE_CBC, b64decode(enc_json['iv']))
        decrypted = cipher.decrypt(b64decode(enc_json['value']))
        decrypted = unpad(decrypted.decode('utf-8'))
        return decrypted

    except Exception as e:
        return encrypted_string
