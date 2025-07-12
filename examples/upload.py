from flai.api import upload
from pathlib import Path
import json
flaiUpload = upload.FlaiUpload()

output = flaiUpload.upload_file(Path('./examples/test.zip'))

print(json.loads(output))


