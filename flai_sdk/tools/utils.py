import psutil
import GPUtil
import time
import cpuinfo
import platform
from datetime import datetime
import subprocess


def get_mac_adresses() -> list:
    """
    Return a list of unique, non-zero MAC addresses for all interfaces.
    Works cross-platform (Windows, Linux, macOS) with no extra dependencies.
    """
    macs = set()

    for addrs in psutil.net_if_addrs().values():
        for addr in addrs:
            address = addr.address
            # match exactly six pairs of hex digits separated by colons
            parts = address.split(':')
            if len(parts) == 6 and all(len(p) == 2 for p in parts):
                mac = address.lower()
                # skip the all-zero “null” MAC
                if mac != '00:00:00:00:00:00':
                    macs.add(mac)
                    
    return list(macs)


def get_motherboard_serial() -> str:
    try:
        if platform.system() == "Windows":
            command = "wmic baseboard get serialnumber"
        elif platform.system() == "Linux":
            command = "cat /sys/class/dmi/id/board_serial"
        elif platform.system() == "Darwin":
            command = "ioreg -l | grep IOPlatformSerialNumber"
        else:
            return ''

        serial = subprocess.check_output(command, shell=True).decode().strip()
        return serial.split('\n')[1] if platform.system() == "Windows" else serial

    except Exception as e:
        return ''


def get_hard_drive_serial():
    try:
        if platform.system() == "Windows":
            command = "wmic diskdrive get serialnumber"
        elif platform.system() == "Linux":
            command = "udevadm info --query=all --name=/dev/sda | grep ID_SERIAL"
        else:
            return ''

        serial = subprocess.check_output(command, shell=True).decode().strip()
        return serial.split('\n')[1] if platform.system() == "Windows" else serial

    except Exception as e:
        return ''


def create_local_machine_info() -> dict:

    try:
        subprocess.check_output('nvidia-smi')
        gpu_list = ', '.join([g.name for g in GPUtil.getGPUs()])
    except Exception as e:
        gpu_list = ''

    try:
        # this takes few seconds to get the whole cpu info
        cpu_info = cpuinfo.get_cpu_info()
        cpu_name = cpu_info['brand_raw']
        cpu_count = cpu_info['count']
        cpu_freq = cpu_info['hz_advertised'][0]
    except Exception as e:
        cpu_name = ''
        cpu_count = 0
        cpu_freq = 0

    try:
        total_memory = psutil.virtual_memory().total / 1024 ** 3
    except Exception as e:
        total_memory = 0

    mac_addrs = get_mac_adresses()
    mac_addr = mac_addrs[0] if len(mac_addrs) > 0 else ""

    return {
        'total_memory': total_memory,
        'cpu_count': cpu_count,
        'cpu_name': cpu_name,
        # 'cpu_freq': cpu_freq,
        'gpus': gpu_list,
        'mac_addresses': mac_addr,
        # not sure if we really need those two additional values, they also raise some access warnings
        # 'motherboard_serial': get_motherboard_serial(),
        # 'hard_drive_serial': get_hard_drive_serial(),
    }


def get_os_info() -> str:

    # should work in Linux distros
    try:
        hostnamectl = subprocess.run(['hostnamectl'], capture_output=True)
        hostinfo = hostnamectl.stdout.decode().split('\n')
        info = []
        for line in hostinfo:
            if 'System' in line or 'Kernel' in line:
                info.append(line.strip())
        return ' '.join(info)
    except Exception as e:
        pass

    # at leas some info should be available even if run in Docker
    try:
        uname = subprocess.run(['uname', '-r'], capture_output=True)
        return f'Kernel: {uname.stdout.decode().strip()}'
    except Exception as e:
        pass

    # TODO: other OS versions

    return 'unkwnown'


def create_node_completed_payload(flow: dict, flow_execution_id: str,
                                  node_id: str, node_finished_status: bool,
                                  dataset_stats={},
                                  execution_time=0,
                                  dataset_id=None,
                                  ai_model_id=None,
                                  start_time=None) -> dict:

    for flow_node in flow['flow_nodes']:
        if flow_node['id'] == node_id:
            break

    return {
            "payload": {
                "flow_id": flow["id"],
                "flow_execution_id": flow_execution_id,
                "status": node_finished_status,
                "started_at": datetime.fromtimestamp(start_time if start_time is not None else time.time()).strftime('%Y-%m-%d %H:%M:%S'),
                "finished_at": datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'),
                "execution_time": execution_time,
                "node_settings": {
                    "options": {
                        "dataset_id": "null" if dataset_id is None else dataset_id,
                        "ai_model_id": "null" if ai_model_id is None else ai_model_id
                    },
                    "flow_node_definition_id": flow_node["flow_node_definition_id"],
                    "flow_node_execution_id": flow_node["flow_node_execution_id"],
                    # things break if you put writer here as it has no valid target dataset_id
                    "type": "processor"  # flow_node["type"]
                },
                "billing": {
                    "runtime_environment": "local",
                    "values": [{"resource": resource, "value": value} for resource, value in dataset_stats.items()]
                }
            }
        }
