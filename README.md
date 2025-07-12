# Flai SDK
    
The Flai SDK is a command-line toolset for interacting with the Flai web app. It is also used by our [QGIS plugin](https://plugins.qgis.org/).


## Install

### From PyPI

```bash
pip install flai-sdk
```

### From source

1. Clone the repo and enter the directory:

    ```bash
    git clone https://github.com:flai-ai/flai-sdk.git
    cd flai-sdk
    ```

2. (Optional) Create and activate a virtual environment.

    **With Conda**

    ```bash
    conda create --name flai-sdk
    conda activate flai-sdk
    ```

    **With venv**

    ```bash
    python3(.VERSION) -m venv ~/.python-virtual-env/flai-sdk
    source ~/.python-virtual-env/flai-sdk/bin/activate
    ```

3. Install in “editable” mode in it's directory:

    `pip install -e .`


## First-time setup

To use our package you will need to call `login` command and pass at least two arguments for authorization (see **Tips** below). 

```bash
flai-sdk login
```

This command will create a json file under path `$HOME/.flai` (Linux / macOS / Windows - Powershell) or `%USERPROFILE%/.flai` (Windows - cmd).

### **Tips:**

 * **`flai_access_token`**
     - can be found on [Flai web app](https://app.flai.ai/#/admin/pages:user-settings?tab=access_tokens) or 
     - by going to our Web App at `flai.ai` > Sign in > Click your `icon` > Select `Settings` from menu > Click `Access tokens` tab > Click `Add new personal access token`
 * **`flai_host`**
     - set it to https://api.flai.ai/


## Examples

### Upload a dataset to a project 

Upload all `.las`/`.laz` files in the current folder to a project.

```bash
# simple example
flai-sdk upload-dataset --project_id PROJECT_NAME --dataset_name DATASET_NAME FILES

# working example
flai-sdk upload-dataset --project_id "Staring project" --dataset_name "Testing upload" "*.la?"

# compact version
flai-sdk upload-dataset -p "Staring project" -n "Testing upload" "*.la?"
```

The flag `--project_id / -p` can be omitted. In this case, the data will not be assigned to a project and will be shown in the catalog on your instance of our web app.

### Download dataset

```bash
flai-sdk download-dataset -d "59d66bfc-c2a4-4e91-91f3-2f469078297b" "downloaded files.zip"
```


## Explore commands

To see what arguments our SDK expects you can start from initial command and then add `--help` to see more hints.

```bash
# to see all available options
flai-sdk --help

# let's say we want to know what option 'download-flainet-model' expects
flai-sdk download-flainet-model --help

# and that is it :)
```