import ipaddress
import math


def calculate_prefix(hosts: int) -> int:
    
    needed = hosts + 2  # réseau + broadcast
    bits = math.ceil(math.log2(needed))
    return 32 - bits


def get_existing_subnets(report: dict) -> list:
    """
    Extrait les subnets déjà présents dans le report.
    """
    existing = []
    subnets = report.get("network_context", {}).get("subnets", [])

    for item in subnets:
        subnet_str = item.get("subnet")
        if subnet_str:
            try:
                existing.append(ipaddress.ip_network(subnet_str, strict=False))
            except Exception:
                pass

    return existing


def get_existing_zone_names(report: dict) -> list:
    """
    Extrait les zones déjà existantes dans le report.
    """
    zones = report.get("network_context", {}).get("zones", [])
    return [z.get("zone_name") for z in zones if z.get("zone_name")]


def overlaps_any(candidate, existing_networks) -> bool:
    """
    Vérifie si un subnet overlap avec des subnets existants.
    """
    for net in existing_networks:
        if candidate.overlaps(net):
            return True
    return False


def generate_vlsm_detailed(report: dict, base_network: str, requirements: list):
    

    network = ipaddress.ip_network(base_network, strict=False)

    existing_subnets = get_existing_subnets(report)
    existing_zone_names = set(get_existing_zone_names(report))

    skipped_zones = []
    zones_to_allocate = []

    #  Nettoyer les besoins utilisateur
    for item in requirements:
        zone_name = item.get("zone_name")
        required_hosts = item.get("required_hosts")

        if not zone_name or required_hosts is None:
            continue

        # ignorer les zones déjà présentes dans le réseau
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

    #  Trier du plus grand au plus petit
    sorted_requirements = sorted(
        zones_to_allocate,
        key=lambda x: x["required_hosts"],
        reverse=True
    )

    reserved_networks = existing_subnets.copy()
    planned = []
    vlan_id = 10

    #  Allocation propre
    for item in sorted_requirements:
        zone_name = item["zone_name"]
        hosts = item["required_hosts"]
        prefix = calculate_prefix(hosts)

        subnet = None

        for candidate in network.subnets(new_prefix=prefix):
            if not overlaps_any(candidate, reserved_networks):
                subnet = candidate
                reserved_networks.append(candidate)
                break

        if subnet is None:
            planned.append({
                "id": vlan_id,
                "departement": zone_name,
                "status": "failed",
                "error": "Pas assez d'espace disponible"
            })
            vlan_id += 10
            continue

        hosts_list = list(subnet.hosts())

        planned.append({
            "id": vlan_id,
            "departement": zone_name,
            "status": "planned",
            "subnet": str(subnet),
            "gateway": str(hosts_list[0]) if hosts_list else None,
            "broadcast": str(subnet.broadcast_address),
            "mask": str(subnet.netmask),
            "usable_hosts": len(hosts_list),
            "prefix": subnet.prefixlen
        })

        vlan_id += 10

    return {
        "base_network": str(network),
        "existing_subnets": [str(net) for net in existing_subnets],
        "skipped_zones": skipped_zones,
        "planned_subnets": planned
    }