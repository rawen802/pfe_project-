import subprocess


def run_network_deployment():
    cmd = [
        "ansible-playbook",
        "playbooks/deploy_configs.yml",
        "-i",
        "inventory/hosts.yml"
    ]

    result = subprocess.run(
        cmd,
        cwd="ansible",
        capture_output=True,
        text=True
    )

    return {
        "status": "success" if result.returncode == 0 else "failed",
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "command": " ".join(cmd)
    }