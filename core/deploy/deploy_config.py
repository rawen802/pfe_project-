import os
import subprocess
from pathlib import Path


def find_project_root():
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / "ansible").exists():
            return parent

    return Path.cwd()


def run_network_deployment():
    base_dir = find_project_root()
    ansible_dir = base_dir / "ansible"

    inventory_file = ansible_dir / "inventory" / "hosts.yml"
    playbook_file = ansible_dir / "playbooks" / "deploy_configs.yml"

    if not ansible_dir.exists():
        return {
            "status": "failed",
            "error": f"Ansible directory not found: {ansible_dir}",
            "base_dir": str(base_dir)
        }

    if not inventory_file.exists():
        return {
            "status": "failed",
            "error": f"Inventory not found: {inventory_file}",
            "base_dir": str(base_dir)
        }

    if not playbook_file.exists():
        return {
            "status": "failed",
            "error": f"Playbook not found: {playbook_file}",
            "base_dir": str(base_dir)
        }

    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    env["ANSIBLE_PARAMIKO_KEX_ALGORITHMS"] = "+diffie-hellman-group1-sha1"

    cmd = [
        "ansible-playbook",
        "-i",
        str(inventory_file),
        str(playbook_file)
    ]

    result = subprocess.run(
        cmd,
        cwd=str(ansible_dir),
        capture_output=True,
        text=True,
        env=env,
        timeout=120
    )

    return {
        "status": "success" if result.returncode == 0 else "failed",
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command": " ".join(cmd),
        "cwd": str(ansible_dir),
        "base_dir": str(base_dir),
        "inventory_file": str(inventory_file),
        "playbook_file": str(playbook_file)
    }