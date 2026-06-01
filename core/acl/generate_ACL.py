import ipaddress


def normalize_name(value):
    if value is None:
        return ""
    return str(value).strip().upper()


def is_any(value):
    return normalize_name(value) in ["ANY", "ALL", "ALL_VLANS", "ANYWHERE"]


def wildcard_from_subnet(subnet: str):
    if is_any(subnet):
        return "any", ""

    net = ipaddress.ip_network(subnet, strict=False)
    wildcard = ipaddress.IPv4Address(int(net.hostmask))
    return str(net.network_address), str(wildcard)


def extract_vlan_id(value):
    """
    Extract VLAN ID dynamically from values like:
    10, "10", "VLAN_10", "VLAN10", "Vlan10".
    """
    if value is None:
        return None

    text = str(value).strip().upper()

    if text.isdigit():
        return int(text)

    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return int(digits)

    return None


def find_core_device(report: dict):
    """
    Find the core/L3 device dynamically from the discovery report.
    Fallback: SW-CORE only if the report does not provide enough info.
    """
    topology_devices = report.get("topology", {}).get("devices", [])
    inventory_devices = report.get("inventory", {}).get("devices", [])
    all_devices = inventory_devices if inventory_devices else topology_devices

    for device in all_devices:
        role = normalize_name(device.get("role") or device.get("type"))
        hostname = device.get("hostname") or device.get("name")

        if "CORE" in role and hostname:
            return hostname

    routing_devices = report.get("network_context", {}).get("routing_devices", [])
    for device in routing_devices:
        hostname = device.get("hostname") or device.get("name")
        if hostname:
            return hostname

    site_core = report.get("site", {}).get("core_device", {})
    if isinstance(site_core, dict):
        hostname = site_core.get("hostname") or site_core.get("name")
        if hostname:
            return hostname

    return "SW-CORE"


def find_zone(report: dict, zone_name: str):
    if is_any(zone_name):
        return None

    wanted = normalize_name(zone_name)
    zones = report.get("network_context", {}).get("zones", [])

    for zone in zones:
        name = (
            zone.get("zone_name")
            or zone.get("name")
            or zone.get("departement")
            or zone.get("department")
        )

        if normalize_name(name) == wanted:
            return zone

    return None


def find_zone_subnet(report: dict, zone_name: str):
    if is_any(zone_name):
        return "any"

    zone = find_zone(report, zone_name)

    if zone:
        subnet = zone.get("subnet") or zone.get("network")
        if subnet:
            return subnet

    wanted = normalize_name(zone_name)

    subnets = report.get("network_context", {}).get("subnets", [])
    for item in subnets:
        item_zone = (
            item.get("zone")
            or item.get("zone_name")
            or item.get("departement")
            or item.get("department")
        )

        if normalize_name(item_zone) == wanted:
            return item.get("subnet") or item.get("network")

    vlans = report.get("network_context", {}).get("vlans", [])
    for vlan in vlans:
        vlan_name = (
            vlan.get("zone_name")
            or vlan.get("name")
            or vlan.get("vlan_name")
        )

        if normalize_name(vlan_name) == wanted:
            subnet = vlan.get("subnet") or vlan.get("network")
            if subnet:
                return subnet

    return None


def infer_vlan_interface(report: dict, zone_name: str):
    """
    Dynamically infer SVI interface from report.
    If source/destination is ANY, no SVI can be inferred from it.
    """
    if is_any(zone_name):
        return None

    wanted = normalize_name(zone_name)
    candidates = []

    zone = find_zone(report, zone_name)
    if zone:
        candidates.append(zone)

    candidates.extend(report.get("network_context", {}).get("vlans", []))
    candidates.extend(report.get("network_context", {}).get("subnets", []))

    for item in candidates:
        if not isinstance(item, dict):
            continue

        names = [
            item.get("zone_name"),
            item.get("name"),
            item.get("vlan_name"),
            item.get("zone"),
            item.get("departement"),
            item.get("department"),
        ]

        matches = any(normalize_name(name) == wanted for name in names)

        item_vlan_id = item.get("vlan_id") or item.get("vlan") or item.get("id")
        wanted_vlan_id = extract_vlan_id(zone_name)

        if not matches and wanted_vlan_id and extract_vlan_id(item_vlan_id) == wanted_vlan_id:
            matches = True

        if not matches:
            continue

        direct_interface = (
            item.get("gateway_interface")
            or item.get("interface")
            or item.get("svi")
            or item.get("svi_interface")
        )

        if direct_interface:
            return str(direct_interface)

        vlan_id = extract_vlan_id(item_vlan_id)
        if vlan_id:
            return f"Vlan{vlan_id}"

    vlan_id_from_name = extract_vlan_id(zone_name)
    if vlan_id_from_name:
        return f"Vlan{vlan_id_from_name}"

    return None


def get_existing_acls(report: dict) -> list:
    devices = report.get("inventory", {}).get("devices", [])
    existing = []

    for device in devices:
        for acl in device.get("existing_acls", []):
            existing.append({
                "device": device.get("hostname"),
                "acl_name": acl.get("name") or acl.get("acl_name"),
                "rules": acl.get("rules", [])
            })

    return existing


def find_acl_by_name(existing_acls: list, acl_name: str):
    for acl in existing_acls:
        if normalize_name(acl.get("acl_name")) == normalize_name(acl_name):
            return acl
    return None


def choose_acl_application(
    report,
    source_zone,
    destination_zone,
    source_site=None,
    destination_site=None
):
    firewalls = report.get("network_context", {}).get("firewalls", [])
    acl_points = report.get("network_context", {}).get("acl_points", [])

    src = find_zone(report, source_zone)
    dst = find_zone(report, destination_zone)

    if source_site and destination_site and source_site != destination_site:
        routing = report.get("network_context", {}).get("routing_devices", [])
        for r in routing:
            if r.get("type") == "EDGE_ROUTER":
                return {
                    "device": r.get("hostname"),
                    "interface": "WAN",
                    "direction": "out",
                    "reason": "multi-site"
                }

    sensitive = ["SERVERS", "SERVER", "DMZ", "ADMIN", "SECURITY"]

    if firewalls and (
        normalize_name(source_zone) in sensitive
        or normalize_name(destination_zone) in sensitive
    ):
        return {
            "device": firewalls[0].get("hostname"),
            "interface": firewalls[0].get("interface"),
            "direction": "in",
            "reason": "firewall"
        }

    if src and src.get("gateway_interface"):
        return {
            "device": src.get("gateway_device") or src.get("device") or find_core_device(report),
            "interface": src.get("gateway_interface"),
            "direction": "in",
            "reason": "source"
        }

    if dst and dst.get("gateway_interface") and is_any(source_zone):
        return {
            "device": dst.get("gateway_device") or dst.get("device") or find_core_device(report),
            "interface": dst.get("gateway_interface"),
            "direction": "out",
            "reason": "destination"
        }

    # Dynamic inference: ACL is usually applied inbound on the SVI of the source VLAN.
    # If source is ANY, fallback to destination SVI outbound.
    src_interface = infer_vlan_interface(report, source_zone)
    if src_interface:
        return {
            "device": find_core_device(report),
            "interface": src_interface,
            "direction": "in",
            "reason": "source_vlan_interface"
        }

    dst_interface = infer_vlan_interface(report, destination_zone)
    if dst_interface:
        return {
            "device": find_core_device(report),
            "interface": dst_interface,
            "direction": "out",
            "reason": "destination_vlan_interface"
        }

    if acl_points:
        return {
            "device": acl_points[0].get("device") or find_core_device(report),
            "interface": acl_points[0].get("interface"),
            "direction": "in",
            "reason": "fallback"
        }

    return {
        "device": find_core_device(report),
        "interface": None,
        "direction": "in",
        "reason": "default_core"
    }


def build_rule(source, destination, protocol, action, port=None):
    return {
        "action": action,
        "protocol": protocol or "ip",
        "source": source,
        "destination": destination,
        "port": port
    }


def process_create(report, existing_acls, policy):
    src_zone = policy.get("source_zone")
    dst_zone = policy.get("destination_zone")

    src_subnet = find_zone_subnet(report, src_zone)
    dst_subnet = find_zone_subnet(report, dst_zone)

    if not src_subnet or not dst_subnet:
        available_zones = [
            z.get("zone_name") or z.get("name")
            for z in report.get("network_context", {}).get("zones", [])
        ]

        return None, {
            "error": "zone not found",
            "source_zone": src_zone,
            "destination_zone": dst_zone,
            "source_subnet": src_subnet,
            "destination_subnet": dst_subnet,
            "available_zones": available_zones
        }

    acl_name = policy.get("acl_name") or (
        f"{policy.get('action', 'deny').upper()}_{src_zone}_TO_{dst_zone}"
    )

    if find_acl_by_name(existing_acls, acl_name):
        return None, "ACL already exists"

    target = choose_acl_application(
        report,
        src_zone,
        dst_zone,
        policy.get("source_site"),
        policy.get("destination_site")
    )

    rule = build_rule(
        src_subnet,
        dst_subnet,
        policy.get("protocol", "ip"),
        policy.get("action", "deny"),
        policy.get("port")
    )

    return {
        "operation": "create",
        "device": target["device"],
        "acl_name": acl_name,
        "rules": [rule],
        "apply_interface": target["interface"],
        "apply_direction": target["direction"],
        "interface": target["interface"],
        "direction": target["direction"],
        "placement": target,
        "reason": target["reason"]
    }, None


def process_update(report, existing_acls, policy):
    acl_name = policy.get("acl_name")

    existing = find_acl_by_name(existing_acls, acl_name)
    if not existing:
        return None, "ACL not found"

    src_subnet = find_zone_subnet(report, policy.get("source_zone"))
    dst_subnet = find_zone_subnet(report, policy.get("destination_zone"))

    if not src_subnet or not dst_subnet:
        return None, "zone not found"

    target = choose_acl_application(
        report,
        policy.get("source_zone"),
        policy.get("destination_zone"),
        policy.get("source_site"),
        policy.get("destination_site")
    )

    new_rule = build_rule(
        src_subnet,
        dst_subnet,
        policy.get("protocol", "ip"),
        policy.get("action", "deny"),
        policy.get("port")
    )

    return {
        "operation": "update",
        "device": existing["device"],
        "acl_name": acl_name,
        "old_rules": existing["rules"],
        "new_rules": [new_rule],
        "apply_interface": target["interface"],
        "apply_direction": target["direction"],
        "interface": target["interface"],
        "direction": target["direction"],
        "placement": target,
        "reason": target["reason"]
    }, None


def process_delete(existing_acls, policy):
    acl_name = policy.get("acl_name")

    existing = find_acl_by_name(existing_acls, acl_name)
    if not existing:
        return None, "ACL not found"

    return {
        "operation": "delete",
        "device": existing["device"],
        "acl_name": acl_name,
        "old_rules": existing["rules"]
    }, None


def process_acl_policies(report: dict, policies: list):
    existing_acls = get_existing_acls(report)

    result = {
        "created": [],
        "updated": [],
        "deleted": [],
        "errors": []
    }

    for policy in policies:
        op = policy.get("operation", "create")

        if op == "create":
            r, e = process_create(report, existing_acls, policy)
            if e:
                result["errors"].append(e)
            else:
                result["created"].append(r)

        elif op == "update":
            r, e = process_update(report, existing_acls, policy)
            if e:
                result["errors"].append(e)
            else:
                result["updated"].append(r)

        elif op == "delete":
            r, e = process_delete(existing_acls, policy)
            if e:
                result["errors"].append(e)
            else:
                result["deleted"].append(r)

    return result
