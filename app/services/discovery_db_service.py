from app.database.database import (
    add_device,
    add_vlan_db,
    add_log,
    save_architecture,
    save_report_file,
    add_report,
)


def save_discovery_report_to_db(report: dict, user_id: int | None = None):
    """
    Sauvegarde en base + fichier le rapport de découverte.
    """
    site_name = report.get("site", {}).get("site_name", "SITE")
    topology = report.get("topology", {})
    devices = topology.get("devices", [])
    links = topology.get("links", [])
    inventory_devices = report.get("inventory", {}).get("devices", [])

    device_map = {}
    saved_devices = 0
    saved_links = 0
    saved_vlans = 0
    errors = []

    # 1) Sauvegarder les devices
    for device in devices:
        try:
            device_id = add_device(
                hostname=device.get("hostname"),
                ip=device.get("ip"),
                type_device=device.get("role", "UNKNOWN")
            )
            device_map[device.get("hostname")] = device_id
            saved_devices += 1
        except Exception as e:
            errors.append(f"Device save failed for {device.get('hostname')}: {e}")

    # 2) Sauvegarder les liens
    try:
        save_architecture(devices, links, device_map)
        saved_links = len(links)
    except Exception as e:
        errors.append(f"Link save failed: {e}")

    # 3) Sauvegarder les VLANs par équipement
    for device in inventory_devices:
        hostname = device.get("hostname")
        device_id = device_map.get(hostname)

        if not device_id:
            continue

        for vlan in device.get("vlans", []):
            try:
                add_vlan_db(
                    vlan_id=vlan.get("id"),
                    vlan_name=vlan.get("name"),
                    device_id=device_id
                )
                saved_vlans += 1
            except Exception as e:
                errors.append(f"VLAN save failed on {hostname}: {e}")

    # 4) Sauvegarder le rapport complet dans un fichier JSON
    try:
        report_name = f"discovery_report_{site_name}"
        file_path = save_report_file(report_name, report)
        report_id = add_report(report_name, user_id, file_path)
    except Exception as e:
        file_path = None
        report_id = None
        errors.append(f"Report file save failed: {e}")

    # 5) Ajouter un log
    try:
        add_log(
            action="DISCOVER_SITE",
            device_id=None,
            user_id=user_id,
            module="DISCOVERY",
            status="success" if not errors else "partial_success",
            extra={
                "site_name": site_name,
                "saved_devices": saved_devices,
                "saved_links": saved_links,
                "saved_vlans": saved_vlans,
                "report_id": report_id,
                "file_path": file_path,
                "errors": errors
            }
        )
    except Exception:
        pass

    return {
        "saved_devices": saved_devices,
        "saved_links": saved_links,
        "saved_vlans": saved_vlans,
        "report_id": report_id,
        "file_path": file_path,
        "errors": errors
    }