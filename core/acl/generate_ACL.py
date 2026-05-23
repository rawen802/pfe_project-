def find_zone(report: dict, zone_name: str):
    zones = report.get("network_context", {}).get("zones", [])
    for zone in zones:
        if zone.get("zone_name") == zone_name:
            return zone
    return None


def find_zone_subnet(report: dict, zone_name: str):
    zone = find_zone(report, zone_name)
    if zone:
        return zone.get("subnet")
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
        if acl.get("acl_name") == acl_name:
            return acl
    return None





def choose_acl_application(report, source_zone, destination_zone, source_site=None, destination_site=None):
    zones = report.get("network_context", {}).get("zones", [])
    firewalls = report.get("network_context", {}).get("firewalls", [])
    acl_points = report.get("network_context", {}).get("acl_points", [])

    src = find_zone(report, source_zone)
    dst = find_zone(report, destination_zone)

    #  MULTI-SITE
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

    #  FIREWALL SI SENSIBLE
    sensitive = ["SERVERS", "DMZ", "ADMIN"]
    if firewalls and (source_zone in sensitive or destination_zone in sensitive):
        return {
            "device": firewalls[0].get("hostname"),
            "interface": None,
            "direction": "in",
            "reason": "firewall"
        }

    # SOURCE 
    if src and src.get("gateway_interface"):
        return {
            "device": src.get("gateway_device"),
            "interface": src.get("gateway_interface"),
            "direction": "in",
            "reason": "source"
        }

    # DESTINATION
    if dst and dst.get("gateway_interface"):
        return {
            "device": dst.get("gateway_device"),
            "interface": dst.get("gateway_interface"),
            "direction": "out",
            "reason": "destination"
        }

    # 5FALLBACK
    if acl_points:
        return {
            "device": acl_points[0].get("device"),
            "interface": None,
            "direction": "in",
            "reason": "fallback"
        }

    return {
        "device": None,
        "interface": None,
        "direction": None,
        "reason": "none"
    }






def build_rule(source, destination, protocol, action, port=None):
    return {
        "action": action,
        "protocol": protocol,
        "source": source,
        "destination": destination,
        "port": port
    }


# =========================
# CREATE / UPDATE / DELETE
# =========================

def process_create(report, existing_acls, policy):
    src_zone = policy.get("source_zone")
    dst_zone = policy.get("destination_zone")

    src_subnet = find_zone_subnet(report, src_zone)
    dst_subnet = find_zone_subnet(report, dst_zone)

    if not src_subnet or not dst_subnet:
        return None, "zone not found"

    acl_name = policy.get("acl_name") or f"{policy['action'].upper()}_{src_zone}_TO_{dst_zone}"

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
        policy.get("protocol", "any"),
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
        "reason": target["reason"]
    }, None


def process_update(report, existing_acls, policy):
    acl_name = policy.get("acl_name")

    existing = find_acl_by_name(existing_acls, acl_name)
    if not existing:
        return None, "ACL not found"

    src_subnet = find_zone_subnet(report, policy.get("source_zone"))
    dst_subnet = find_zone_subnet(report, policy.get("destination_zone"))

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
        policy.get("protocol"),
        policy.get("action"),
        policy.get("port")
    )

    return {
        "operation": "update",
        "device": existing["device"],
        "acl_name": acl_name,
        "old_rules": existing["rules"],
        "new_rules": [new_rule],
        "apply_interface": target["interface"],
        "apply_direction": target["direction"]
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


# =========================
# MAIN FUNCTION
# =========================

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
            if e: result["errors"].append(e)
            else: result["created"].append(r)

        elif op == "update":
            r, e = process_update(report, existing_acls, policy)
            if e: result["errors"].append(e)
            else: result["updated"].append(r)

        elif op == "delete":
            r, e = process_delete(existing_acls, policy)
            if e: result["errors"].append(e)
            else: result["deleted"].append(r)

    return result