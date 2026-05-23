from pathlib import Path
import yaml


def build_inventory(devices: list, output_file: str = "ansible/inventory/hosts.yml"):
    inventory = {
        "all": {
            "hosts": {}
        }
    }

    for device in devices:
        inventory["all"]["hosts"][device["hostname"]] = {
            "ansible_host": device["ip"],
            "ansible_user": device["username"],
            "ansible_password": device["password"],
            "ansible_connection": "ansible.netcommon.network_cli",
            "ansible_network_os": "cisco.ios.ios",
            "ansible_become": True,
            "ansible_become_method": "enable",
            "ansible_become_password": device.get("enable_password", device["password"])
        }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(inventory, f, sort_keys=False, allow_unicode=True)

    return str(output_path)