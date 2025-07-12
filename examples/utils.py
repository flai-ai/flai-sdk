from flai_sdk import utils
from pathlib import Path

out = utils.zip_all_files(Path('./examples'), pattern='*.py', name='test-py')
