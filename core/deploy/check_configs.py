from pathlib import Path


def check_network_config_files(devices: list, config_folder: str = "output/configs"):
    missing = []
    existing = {}

    for device in devices:
        hostname = device["hostname"]
        cfg_file = Path(config_folder) / f"{hostname}.cfg"

        if not cfg_file.exists():
            missing.append(hostname)
        else:
            existing[hostname] = str(cfg_file)

    return {
        "missing": missing,
        "existing": existing
    }