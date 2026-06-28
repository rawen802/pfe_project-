import os
import sys
import subprocess
from pathlib import Path


def find_project_root() -> Path:
    current = Path(__file__).resolve()

    for parent in [current.parent] + list(current.parents):
        if (
            (parent / "ansible").exists()
            and (parent / "output").exists()
            and (parent / "app").exists()
        ):
            return parent

    return Path.cwd()


def run_deployment():
    base_dir = find_project_root()
    ansible_dir = base_dir / "ansible"

    inventory_file = ansible_dir / "inventory" / "hosts.yml"
    playbook_file = ansible_dir / "playbooks" / "deploy_acl_configs.yml"
    config_dir = base_dir / "output" / "acl_configs"

    if not ansible_dir.exists():
        return {
            "status": "failed",
            "return_code": -1,
            "stdout": "",
            "stderr": f"Ansible directory not found: {ansible_dir}",
            "command": "",
            "cwd": str(ansible_dir),
        }

    if not inventory_file.exists():
        return {
            "status": "failed",
            "return_code": -1,
            "stdout": "",
            "stderr": f"Inventory file not found: {inventory_file}",
            "command": "",
            "cwd": str(ansible_dir),
        }

    if not playbook_file.exists():
        return {
            "status": "failed",
            "return_code": -1,
            "stdout": "",
            "stderr": f"Playbook file not found: {playbook_file}",
            "command": "",
            "cwd": str(ansible_dir),
        }

    if not config_dir.exists():
        return {
            "status": "failed",
            "return_code": -1,
            "stdout": "",
            "stderr": f"ACL config directory not found: {config_dir}",
            "command": "",
            "cwd": str(ansible_dir),
        }

    env = os.environ.copy()

    venv_site_packages = (
        base_dir
        / "venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )

    if venv_site_packages.exists():
        env["PYTHONPATH"] = str(venv_site_packages)

    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    env["ANSIBLE_PARAMIKO_KEX_ALGORITHMS"] = "+diffie-hellman-group1-sha1"
    env["ANSIBLE_PARAMIKO_HOST_KEY_ALGORITHMS"] = "+ssh-rsa"
    env["ANSIBLE_PARAMIKO_PUBKEY_ALGORITHMS"] = "+ssh-rsa"

    cmd = [
        "ansible-playbook",
        "-i",
        str(inventory_file),
        str(playbook_file),
    ]

    try:
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
            "ansible_dir": str(ansible_dir),
            "inventory_file": str(inventory_file),
            "playbook_file": str(playbook_file),
            "config_dir": str(config_dir),
        }

    except subprocess.TimeoutExpired as e:
        return {
            "status": "failed",
            "return_code": -1,
            "stdout": e.stdout or "",
            "stderr": "Timeout: le déploiement ACL a dépassé 120 secondes.",
            "command": " ".join(cmd),
            "cwd": str(ansible_dir),
            "ansible_dir": str(ansible_dir),
            "inventory_file": str(inventory_file),
            "playbook_file": str(playbook_file),
            "config_dir": str(config_dir),
        }