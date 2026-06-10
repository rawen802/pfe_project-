#Récuperer les vlans existants depuis le report 

def get_existing_vlans(report: dict):
    
    return report.get("network_context", {}).get("vlans", [])

#Récuperer les zones déja présentes dans le réseau 
def get_existing_zone_names(report: dict):
    
    zones = report.get("network_context", {}).get("zones", [])
    return [z.get("zone_name") for z in zones if z.get("zone_name")]


# Récupère les switches d'accès et de distribution  depuis topology.devices
    
def get_access_and_distribution_switches(report: dict):
    
    devices = report.get("topology", {}).get("devices", [])
    return [
        d for d in devices
        if d.get("role") in ["ACCESS_SWITCH", "DISTRIBUTION_SWITCH"]
    ]

#Récupère les switches coeur
def get_core_switches(report: dict):
    
    devices = report.get("topology", {}).get("devices", [])
    return [
        d for d in devices
        if d.get("role") == "SITE_CORE"
    ]


#Récupère les trunks par équipement depuis inventory.devices
def get_trunks_by_device(report: dict):
    
    inventory_devices = report.get("inventory", {}).get("devices", [])
    trunk_map = {}

    for device in inventory_devices:
        trunk_map[device.get("hostname")] = device.get("trunks", [])

    return trunk_map

#Propose le prochain VLAN ID libre
def suggest_next_vlan_id(report: dict, start: int = 10):
    
    existing_vlans = get_existing_vlans(report)
    existing_ids = set()

    for vlan in existing_vlans:
        vlan_id = vlan.get("vlan_id")
        if vlan_id is not None:
            existing_ids.add(vlan_id)

    vlan_id = start
    while vlan_id in existing_ids:
        vlan_id += 10

    return vlan_id

#Choisit les équipements concernés par le nouveau VLAN.
def choose_vlan_targets(report: dict, zone_name: str):
    
    access_switches = get_access_and_distribution_switches(report)
    core_switches = get_core_switches(report)
    trunk_map = get_trunks_by_device(report)

    return {
        "access_switches": [
            {
                "hostname": sw.get("hostname"),
                "ip": sw.get("ip"),
                "role": sw.get("role"),
                "trunks": trunk_map.get(sw.get("hostname"), [])
            }
            for sw in access_switches
        ],
        "core_switches": [
            {
                "hostname": sw.get("hostname"),
                "ip": sw.get("ip"),
                "role": sw.get("role")
            }
            for sw in core_switches
        ]
    }

# Moteur logique 
def process_vlan_requests(report: dict, requested_zones: list):
    result = {
        "created": [],
        "skipped": [],
        "errors": []
    }

    existing_vlans = get_existing_vlans(report)

    used_ids = set()
    vlan_by_zone = {}
    vlan_by_name = {}

    for vlan in existing_vlans:
        vlan_id = vlan.get("vlan_id")
        vlan_name = (
            vlan.get("vlan_name")
            or vlan.get("name")
            or vlan.get("zone")
            or ""
        )

        zone = (
            vlan.get("zone_name")
            or vlan.get("zone")
            or vlan_name
            or ""
        )

        try:
            vlan_id = int(vlan_id)
        except Exception:
            continue

        used_ids.add(vlan_id)

        if zone:
            vlan_by_zone[zone.upper()] = {
                "vlan_id": vlan_id,
                "vlan_name": vlan_name or zone
            }

        if vlan_name:
            vlan_by_name[vlan_name.upper()] = {
                "vlan_id": vlan_id,
                "vlan_name": vlan_name
            }

    next_vlan_id = 10
    while next_vlan_id in used_ids:
        next_vlan_id += 10

    for item in requested_zones:
        zone_name = item.get("zone_name")
        vlan_name = item.get("vlan_name") or zone_name
        required_hosts = item.get("required_hosts", 0)

        if not zone_name:
            result["errors"].append("zone_name is required")
            continue

        zone_key = str(zone_name).upper()
        vlan_key = str(vlan_name).upper()

        existing_match = vlan_by_zone.get(zone_key) or vlan_by_name.get(vlan_key)

        if existing_match:
            selected_vlan_id = existing_match["vlan_id"]
            selected_vlan_name = existing_match["vlan_name"] or vlan_name
            reason = "existing VLAN reused from discovery report"
        else:
            selected_vlan_id = next_vlan_id
            selected_vlan_name = vlan_name
            reason = "new VLAN for business zone"

            used_ids.add(selected_vlan_id)
            while next_vlan_id in used_ids:
                next_vlan_id += 10

        targets = choose_vlan_targets(report, zone_name)

        vlan_data = {
            "operation": "create",
            "zone_name": zone_name,
            "vlan_id": selected_vlan_id,
            "vlan_name": selected_vlan_name,
            "required_hosts": required_hosts,
            "deploy_on": targets["access_switches"],
            "core_switches": targets["core_switches"],
            "needs_trunk_update": True,
            "needs_svi": True,
            "reason": reason
        }

        result["created"].append(vlan_data)

    return result