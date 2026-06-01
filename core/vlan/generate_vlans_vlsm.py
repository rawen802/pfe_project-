import ipaddress
import math


def calculate_prefix(hosts: int) -> int:
    hosts = int(hosts)

    if hosts <= 0:
        raise ValueError("hosts must be positive")

    needed = hosts + 2
    bits = math.ceil(math.log2(needed))
    return 32 - bits


def get_existing_subnets(report: dict) -> list:
    existing = []

    if not isinstance(report, dict):
        return existing

    subnets = report.get("network_context", {}).get("subnets", [])

    for item in subnets:
        if not isinstance(item, dict):
            continue

        subnet_str = item.get("subnet")

        if subnet_str:
            try:
                existing.append(ipaddress.ip_network(str(subnet_str), strict=False))
            except Exception:
                pass

    return existing


def get_existing_zone_names(report: dict) -> list:
    if not isinstance(report, dict):
        return []

    zones = report.get("network_context", {}).get("zones", [])
    names = []

    for z in zones:
        if not isinstance(z, dict):
            continue

        name = z.get("zone_name") or z.get("name")

        if name:
            names.append(str(name).strip().upper())

    return names


def get_existing_vlan_ids(report: dict) -> set:
    vlan_ids = set()

    if not isinstance(report, dict):
        return vlan_ids

    vlans = report.get("network_context", {}).get("vlans", [])

    for vlan in vlans:
        if not isinstance(vlan, dict):
            continue

        vlan_id = (
            vlan.get("id")
            or vlan.get("vlan_id")
            or vlan.get("vlan")
            or vlan.get("number")
        )

        try:
            vlan_ids.add(int(vlan_id))
        except Exception:
            pass

    return vlan_ids


def overlaps_any(candidate, existing_networks) -> bool:
    for net in existing_networks:
        try:
            if candidate.overlaps(net):
                return True
        except Exception:
            pass

    return False


def first_host(subnet):
    try:
        return str(next(subnet.hosts()))
    except StopIteration:
        return None


def usable_host_count(subnet):
    if subnet.version == 4:
        if subnet.prefixlen >= 31:
            return subnet.num_addresses
        return max(subnet.num_addresses - 2, 0)

    return subnet.num_addresses


def generate_vlsm_detailed(report: dict, base_network: str, requirements: list):
    try:
        network = ipaddress.ip_network(str(base_network), strict=False)
    except Exception:
        return {
            "status": "error",
            "error": "Invalid base_network",
            "base_network": base_network,
            "planned_subnets": []
        }

    if not isinstance(requirements, list):
        return {
            "status": "error",
            "error": "requirements must be a list",
            "base_network": str(network),
            "planned_subnets": []
        }

    existing_subnets = get_existing_subnets(report)
    existing_zone_names = set(get_existing_zone_names(report))

    skipped_zones = []
    zones_to_allocate = []

    for item in requirements:
        if not isinstance(item, dict):
            skipped_zones.append({
                "zone_name": None,
                "reason": "Invalid requirement item"
            })
            continue

        zone_name = item.get("zone_name") or item.get("name")
        required_hosts = item.get("required_hosts") or item.get("hosts")

        if not zone_name or required_hosts is None:
            skipped_zones.append({
                "zone_name": zone_name,
                "reason": "Missing zone_name or required_hosts"
            })
            continue

        zone_name = str(zone_name).strip().upper()

        try:
            required_hosts = int(required_hosts)
        except Exception:
            skipped_zones.append({
                "zone_name": zone_name,
                "reason": "Invalid required_hosts"
            })
            continue

        if required_hosts <= 0:
            skipped_zones.append({
                "zone_name": zone_name,
                "reason": "required_hosts must be positive"
            })
            continue

        if zone_name in existing_zone_names:
            skipped_zones.append({
                "zone_name": zone_name,
                "reason": "Zone already exists in report"
            })
            continue

        zones_to_allocate.append({
            "zone_name": zone_name,
            "required_hosts": required_hosts
        })

    sorted_requirements = sorted(
        zones_to_allocate,
        key=lambda x: x["required_hosts"],
        reverse=True
    )

    reserved_networks = existing_subnets.copy()
    planned = []

    used_vlan_ids = get_existing_vlan_ids(report)
    used_vlan_ids.update({1, 1002, 1003, 1004, 1005})

    vlan_id = 10

    for item in sorted_requirements:
        zone_name = item["zone_name"]
        hosts = item["required_hosts"]

        try:
            prefix = calculate_prefix(hosts)
        except Exception as e:
            planned.append({
                "departement": zone_name,
                "zone_name": zone_name,
                "status": "failed",
                "error": str(e)
            })
            continue

        subnet = None

        try:
            candidates = network.subnets(new_prefix=prefix)
        except ValueError:
            planned.append({
                "departement": zone_name,
                "zone_name": zone_name,
                "status": "failed",
                "error": "Required hosts exceed base network capacity"
            })
            continue

        for candidate in candidates:
            if not overlaps_any(candidate, reserved_networks):
                subnet = candidate
                reserved_networks.append(candidate)
                break

        while vlan_id in used_vlan_ids:
            vlan_id += 10

        if subnet is None:
            planned.append({
                "id": vlan_id,
                "departement": zone_name,
                "zone_name": zone_name,
                "status": "failed",
                "error": "Pas assez d'espace disponible"
            })
            vlan_id += 10
            continue

        gateway = first_host(subnet)

        planned.append({
            "id": vlan_id,
            "vlan_id": vlan_id,
            "departement": zone_name,
            "zone_name": zone_name,
            "status": "planned",
            "subnet": str(subnet),
            "gateway": gateway,
            "broadcast": str(subnet.broadcast_address),
            "mask": str(subnet.netmask),
            "usable_hosts": usable_host_count(subnet),
            "required_hosts": hosts,
            "prefix": subnet.prefixlen
        })

        used_vlan_ids.add(vlan_id)
        vlan_id += 10

    return {
        "status": "success",
        "base_network": str(network),
        "existing_subnets": [str(net) for net in existing_subnets],
        "existing_zones": list(existing_zone_names),
        "skipped_zones": skipped_zones,
        "planned_subnets": planned
    }