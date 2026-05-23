from napalm import get_network_driver
import re
import ipaddress
from collections import deque 

def parse_vlans(output: str) -> list:
    vlans = []

    for line in output.splitlines():
        line = line.strip()
        match = re.match(r"^(\d+)\s+(\S+)\s+\S+", line)
        if match:
            vlan_id = int(match.group(1))
            vlan_name = match.group(2)

            if 1 <= vlan_id <= 4094:
                vlans.append({
                    "id": vlan_id,
                    "name": vlan_name
                })

    return vlans


def parse_trunks(output: str) -> list:
    trunks = []

    for line in output.splitlines():
        line = line.strip()

        if line.startswith(("Gi", "Fa", "Te", "Po", "Eth")):
            parts = line.split()
            if len(parts) >= 2:
                trunks.append(parts[0])

    return trunks


def parse_svis(show_ip_int_brief_output: str) -> list:
    svis = []

    for line in show_ip_int_brief_output.splitlines():
        line = line.strip()

        if line.startswith("Vlan"):
            parts = line.split()
            if len(parts) >= 2:
                interface_name = parts[0]
                ip_addr = parts[1]

                if ip_addr.lower() != "unassigned":
                    vlan_match = re.match(r"Vlan(\d+)", interface_name, re.IGNORECASE)
                    vlan_id = int(vlan_match.group(1)) if vlan_match else None

                    svis.append({
                        "vlan": vlan_id,
                        "name": interface_name,
                        "ip": ip_addr,
                        "subnet": None,
                        "gateway": ip_addr
                    })

    return svis


def parse_svi_subnets(show_running_vlan_output: str, svis: list) -> list:
    current_vlan = None
    subnet_map = {}

    for raw_line in show_running_vlan_output.splitlines():
        line = raw_line.strip()

        int_match = re.match(r"^interface\s+Vlan(\d+)", line, re.IGNORECASE)
        if int_match:
            current_vlan = int(int_match.group(1))
            continue

        ip_match = re.match(r"^ip address\s+(\S+)\s+(\S+)", line, re.IGNORECASE)
        if ip_match and current_vlan is not None:
            ip_addr = ip_match.group(1)
            mask = ip_match.group(2)

            try:
                network = ipaddress.ip_network(f"{ip_addr}/{mask}", strict=False)
                subnet_map[current_vlan] = str(network)
            except Exception:
                subnet_map[current_vlan] = None

    for svi in svis:
        vlan_id = svi.get("vlan")
        if vlan_id in subnet_map:
            svi["subnet"] = subnet_map[vlan_id]

    return svis


def parse_routing(output: str) -> bool:
    return "ip routing" in output.lower()


def parse_neighbors(output: str) -> list:
    neighbors = []
    blocks = output.split("-------------------------")

    for block in blocks:
        hostname = None
        ip_addr = None
        platform = None
        local_interface = None
        remote_interface = None

        for line in block.splitlines():
            line = line.strip()

            if line.startswith("Device ID:"):
                hostname = line.replace("Device ID:", "").strip()

            elif "IP address:" in line:
                ip_addr = line.split("IP address:")[-1].strip()

            elif line.startswith("Platform:"):
                platform = line.replace("Platform:", "").split(",")[0].strip()

            elif line.startswith("Interface:") and "Port ID" in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    local_interface = parts[0].replace("Interface:", "").strip()
                    remote_interface = parts[1].split(":")[-1].strip()

        if hostname or ip_addr:
            neighbors.append({
                "neighbor_hostname": hostname,
                "neighbor_ip": ip_addr,
                "platform": platform,
                "local_interface": local_interface,
                "remote_interface": remote_interface,
                "protocol": "CDP"
            })

    return neighbors


def parse_existing_acls(output: str) -> list:
    acls = []
    current_acl = None

    for raw_line in output.splitlines():
        line = raw_line.strip()

        acl_match = re.match(r"^ip access-list (standard|extended)\s+(\S+)", line, re.IGNORECASE)
        if acl_match:
            current_acl = {
                "type": acl_match.group(1).upper(),
                "name": acl_match.group(2),
                "rules": []
            }
            acls.append(current_acl)
            continue

        if current_acl and line and not line.startswith("!"):
            current_acl["rules"].append(line)

    return acls


def discover_one_device(device: dict, logger=None) -> dict:
    """
    Découvre un seul équipement.
    """
    driver = get_network_driver("ios")
    connection = None

    try:
        connection = driver(
            hostname=device["ip"],
            username=device["username"],
            password=device["password"],
            optional_args={"secret": device.get("secret")}
        )

        connection.open()

        facts = connection.get_facts()
        interfaces = connection.get_interfaces()

        cli_output = connection.cli([
            "show vlan brief",
            "show interfaces trunk",
            "show ip interface brief",
            "show running-config | section ^interface Vlan",
            "show running-config | include ^ip routing",
            "show cdp neighbors detail",
            "show running-config | section ^ip access-list"
        ])

        vlans = parse_vlans(cli_output.get("show vlan brief", ""))
        trunks = parse_trunks(cli_output.get("show interfaces trunk", ""))
        svis = parse_svis(cli_output.get("show ip interface brief", ""))
        svis = parse_svi_subnets(
            cli_output.get("show running-config | section ^interface Vlan", ""),
            svis
        )
        routing = parse_routing(cli_output.get("show running-config | include ^ip routing", ""))
        neighbors = parse_neighbors(cli_output.get("show cdp neighbors detail", ""))
        existing_acls = parse_existing_acls(
            cli_output.get("show running-config | section ^ip access-list", "")
        )

        result = {
            "ip": device["ip"],
            "hostname": facts.get("hostname"),
            "model": facts.get("model"),
            "vendor": facts.get("vendor"),
            "os_version": facts.get("os_version"),
            "serial_number": facts.get("serial_number"),
            "uptime": facts.get("uptime"),
            "interfaces": interfaces,
            "neighbors": neighbors,
            "vlans": vlans,
            "trunks": trunks,
            "svis": svis,
            "routing": routing,
            "existing_acls": existing_acls,
            "username": device["username"],
            "password": device["password"],
            "secret": device.get("secret"),
            "reachable": True
        }

        if logger:
            logger.info(f"{device['ip']} discovered successfully")

        return result

    except Exception as e:
        if logger:
            logger.error(f"{device['ip']} connection failed: {e}")

        return {
            "ip": device["ip"],
            "hostname": device.get("hostname", "unknown"),
            "model": device.get("model", ""),
            "vendor": "",
            "os_version": "",
            "serial_number": "",
            "uptime": 0,
            "interfaces": {},
            "neighbors": [],
            "vlans": [],
            "trunks": [],
            "svis": [],
            "routing": False,
            "existing_acls": [],
            "username": device["username"],
            "password": device["password"],
            "secret": device.get("secret"),
            "reachable": False,
            "error": str(e)
        }

    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

def should_explore_neighbor(neighbor: dict) -> bool:
    
    hostname = (neighbor.get("neighbor_hostname") or "").lower()
    platform = (neighbor.get("platform") or "").lower()
    ip_addr = neighbor.get("neighbor_ip")

    if not ip_addr:
        return False

    # On ne veut pas partir vers WAN / MPLS / cloud
    if any(x in hostname for x in ["mpls", "wan", "internet", "cloud"]):
        return False

    allowed = [
        "switch", "catalyst", "2960", "3560", "4500", "6500",
        "router", "2811", "1921",
        "fortinet", "cyberoam", "firewall"
    ]

    return any(x in platform for x in allowed)

def discover_devices(seed_devices, logger=None) -> list:
    
    results = []
    visited_ips = set()
    queue = deque(seed_devices)
    while queue:
        current = queue.popleft()
        current_ip = current.get("ip")

        if not current_ip:
            continue

        if current_ip in visited_ips:
            continue

        visited_ips.add(current_ip)

        if logger:
            logger.info(f"[DISCOVERY] Exploring {current_ip}")

        discovered = discover_one_device(current, logger=logger)
        results.append(discovered)
         # Si l'équipement n'est pas joignable, on ne va pas plus loin
        if not discovered.get("reachable"):
            continue

        neighbors = discovered.get("neighbors", [])

        for neighbor in neighbors:
            if not should_explore_neighbor(neighbor):
                continue

            neighbor_ip = neighbor.get("neighbor_ip")
            if not neighbor_ip:
                continue

            if neighbor_ip in visited_ips:
                continue
            queue.append({
                "hostname": neighbor.get("neighbor_hostname"),
                "ip": neighbor_ip,
                "username": current["username"],
                "password": current["password"],
                "secret": current.get("secret"),
                "model": neighbor.get("platform", "")
            })

    return results    
