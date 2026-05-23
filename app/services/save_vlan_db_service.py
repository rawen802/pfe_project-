from app.database.database import add_vlan_db, connect_db


def get_or_create_device(hostname: str, ip: str = None, role: str = "UNKNOWN"):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM devices WHERE hostname = ?", (hostname,))
    row = cursor.fetchone()

    if row:
        conn.close()
        return row["id"] if hasattr(row, "keys") else row[0]

    cursor.execute("""
        INSERT INTO devices (hostname, ip, type, detected_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (hostname, ip, role))

    conn.commit()
    device_id = cursor.lastrowid
    conn.close()

    return device_id


def save_vlan_result_to_db(vlan_result: dict, device_map: dict):
    saved = 0
    errors = []

    for item in vlan_result.get("created", []):
        vlan_id = item.get("vlan_id")
        vlan_name = item.get("vlan_name")

        for device in item.get("deploy_on", []):
            hostname = device.get("hostname")
            ip = device.get("ip")
            role = device.get("role", "UNKNOWN")

            device_id = device_map.get(hostname)
            if not device_id:
                try:
                    device_id = get_or_create_device(hostname, ip, role)
                    device_map[hostname] = device_id
                except Exception as e:
                    errors.append(f"Failed to create device {hostname}: {str(e)}")
                    continue

            try:
                add_vlan_db(
                    vlan_id=vlan_id,
                    vlan_name=vlan_name,
                    device_id=device_id
                )
                saved += 1
            except Exception as e:
                errors.append(f"Failed to save VLAN {vlan_id} on {hostname}: {str(e)}")

        for core in item.get("core_switches", []):
            hostname = core.get("hostname")
            ip = core.get("ip")
            role = core.get("role", "UNKNOWN")

            device_id = device_map.get(hostname)
            if not device_id:
                try:
                    device_id = get_or_create_device(hostname, ip, role)
                    device_map[hostname] = device_id
                except Exception as e:
                    errors.append(f"Failed to create core device {hostname}: {str(e)}")
                    continue

            try:
                add_vlan_db(
                    vlan_id=vlan_id,
                    vlan_name=vlan_name,
                    device_id=device_id
                )
                saved += 1
            except Exception as e:
                errors.append(f"Failed to save VLAN {vlan_id} on core {hostname}: {str(e)}")

    return {
        "saved_vlans": saved,
        "errors": errors
    }