from napalm import get_network_driver
import re
import ipaddress
import time
from collections import deque

try:
    import paramiko
except Exception:
    paramiko = None


def parse_vlans(output: str) -> list:
    vlans = []
    for line in output.splitlines():
        line = line.strip()
        match = re.match(r"^(\d+)\s+(\S+)\s+\S+", line)
        if match:
            vlan_id = int(match.group(1))
            vlan_name = match.group(2)
            if 1 <= vlan_id <= 4094:
                vlans.append({"id": vlan_id, "name": vlan_name})
    return vlans


def parse_vlan_list(value: str) -> list:
    vlans = []
    if not value:
        return vlans

    value = value.strip()
    if value.lower() in ["none", "all"]:
        return [value.lower()]

    for part in value.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            try:
                start, end = part.split("-", 1)
                vlans.extend(list(range(int(start), int(end) + 1)))
            except Exception:
                vlans.append(part)
        else:
            try:
                vlans.append(int(part))
            except Exception:
                vlans.append(part)

    return vlans


def trunk_template(interface):
    return {
        "interface": interface,
        "mode": None,
        "encapsulation": None,
        "status": None,
        "native_vlan": None,
        "allowed_vlans": [],
        "allowed_active_vlans": [],
        "forwarding_vlans": []
    }


def is_interface_name(value: str) -> bool:
    if not value:
        return False

    value = value.strip()

    if value.lower() == "port":
        return False

    return value.startswith((
        "Gi", "Fa", "Te", "Po", "Eth",
        "Gig", "Fast", "Ten",
        "GigabitEthernet",
        "FastEthernet",
        "TenGigabitEthernet",
        "Port-channel"
    ))


def parse_trunks(output: str) -> list:
    trunks = {}
    section = None

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        lower = line.lower()

        if lower.startswith("port") and "mode" in lower and "encapsulation" in lower:
            section = "status"
            continue

        if "vlans allowed on trunk" in lower:
            section = "allowed"
            continue

        if "vlans allowed and active" in lower:
            section = "allowed_active"
            continue

        if "vlans in spanning tree forwarding state" in lower:
            section = "forwarding"
            continue

        parts = line.split()
        if not parts:
            continue

        interface = parts[0]

        if not is_interface_name(interface):
            continue

        if section == "status" and len(parts) >= 5:
            trunks.setdefault(interface, trunk_template(interface))
            trunks[interface]["mode"] = parts[1]
            trunks[interface]["encapsulation"] = parts[2]
            trunks[interface]["status"] = parts[3]
            trunks[interface]["native_vlan"] = parts[4]

        elif section == "allowed" and len(parts) >= 2:
            trunks.setdefault(interface, trunk_template(interface))
            trunks[interface]["allowed_vlans"] = parse_vlan_list(parts[1])

        elif section == "allowed_active" and len(parts) >= 2:
            trunks.setdefault(interface, trunk_template(interface))
            trunks[interface]["allowed_active_vlans"] = parse_vlan_list(parts[1])

        elif section == "forwarding" and len(parts) >= 2:
            trunks.setdefault(interface, trunk_template(interface))
            trunks[interface]["forwarding_vlans"] = parse_vlan_list(parts[1])

    return list(trunks.values())


def parse_switchport_trunks(output: str) -> list:
    trunks = []
    current = None
    data = {}

    for raw_line in output.splitlines():
        line = raw_line.strip()

        name_match = re.match(r"^Name:\s+(\S+)", line, re.IGNORECASE)

        if name_match:
            if current and data.get("is_trunk"):
                data.pop("is_trunk", None)
                trunks.append(data)

            current = name_match.group(1)
            data = trunk_template(current)
            data["is_trunk"] = False
            continue

        if not current:
            continue

        admin_match = re.match(r"^Administrative Mode:\s+(.+)", line, re.IGNORECASE)
        oper_match = re.match(r"^Operational Mode:\s+(.+)", line, re.IGNORECASE)
        native_match = re.match(r"^Trunking Native Mode VLAN:\s+(\d+)", line, re.IGNORECASE)
        allowed_match = re.match(r"^Trunking VLANs Enabled:\s+(.+)", line, re.IGNORECASE)
        encaps_match = re.match(r"^Administrative Trunking Encapsulation:\s+(.+)", line, re.IGNORECASE)

        if admin_match:
            admin_mode = admin_match.group(1).strip()
            data["mode"] = admin_mode
            if "trunk" in admin_mode.lower():
                data["is_trunk"] = True

        elif oper_match:
            operational_mode = oper_match.group(1).strip()
            data["status"] = operational_mode
            if "trunk" in operational_mode.lower():
                data["is_trunk"] = True

        elif native_match:
            data["native_vlan"] = native_match.group(1)

        elif allowed_match:
            data["allowed_vlans"] = parse_vlan_list(allowed_match.group(1).strip())

        elif encaps_match:
            data["encapsulation"] = encaps_match.group(1).strip()

    if current and data.get("is_trunk"):
        data.pop("is_trunk", None)
        trunks.append(data)

    return trunks


def parse_acl_applications(output: str) -> list:
    applications = []
    current_interface = None

    for raw_line in output.splitlines():
        line = raw_line.strip()

        int_match = re.match(r"^interface\s+(\S+)", line, re.IGNORECASE)

        if int_match:
            current_interface = int_match.group(1)
            continue

        acl_match = re.match(
            r"^ip access-group\s+(\S+)\s+(in|out)",
            line,
            re.IGNORECASE
        )

        if acl_match and current_interface:
            applications.append({
                "interface": current_interface,
                "acl_name": acl_match.group(1),
                "direction": acl_match.group(2).lower()
            })

    return applications


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


def parse_routing(output: str, svis=None) -> bool:
    if "ip routing" in output.lower():
        return True

    routed_svis = [
        svi for svi in (svis or [])
        if svi.get("vlan") not in [1, 99]
    ]

    if len(routed_svis) >= 2:
        return True

    return False


def clean_hostname(hostname: str) -> str:
    if not hostname:
        return hostname

    return hostname.split(".")[0].strip()


def parse_cdp_neighbors(output: str) -> list:
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

        if hostname and ip_addr:
            neighbors.append({
                "neighbor_hostname": clean_hostname(hostname),
                "neighbor_ip": ip_addr,
                "platform": platform,
                "local_interface": local_interface,
                "remote_interface": remote_interface,
                "protocol": "CDP"
            })

    return neighbors


def parse_lldp_neighbors(output: str) -> list:
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

            if line.startswith("System Name:"):
                hostname = line.replace("System Name:", "").strip()

            elif "Management Address:" in line:
                ip_addr = line.split("Management Address:")[-1].strip()

            elif line.startswith("System Description:"):
                platform = line.replace("System Description:", "").strip()

            elif line.startswith("Local Intf:"):
                local_interface = line.replace("Local Intf:", "").strip()

            elif line.startswith("Port id:"):
                remote_interface = line.replace("Port id:", "").strip()

        if hostname and ip_addr:
            neighbors.append({
                "neighbor_hostname": clean_hostname(hostname),
                "neighbor_ip": ip_addr,
                "platform": platform,
                "local_interface": local_interface,
                "remote_interface": remote_interface,
                "protocol": "LLDP"
            })

    return neighbors


def parse_existing_acls(output: str) -> list:
    acls = []
    current_acl = None

    for raw_line in output.splitlines():
        line = raw_line.strip()

        acl_match = re.match(
            r"^ip access-list (standard|extended)\s+(\S+)",
            line,
            re.IGNORECASE
        )

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
    driver = get_network_driver("ios")
    connection = None

    try:
        connection = driver(
            hostname=device["ip"],
            username=device["username"],
            password=device["password"],
            optional_args={
                "secret": device.get("secret") or device.get("password"),
                "timeout": 120,
                "global_delay_factor": 4,
                "read_timeout_override": 90,
                "session_log": f"netmiko_session_{device['ip']}.log"
            }
        )

        connection.open()

        facts = connection.get_facts()
        interfaces = connection.get_interfaces()

        cli_output = connection.cli([
            "show vlan brief",
            "show interfaces trunk",
            "show interfaces switchport",
            "show ip interface brief",
            "show running-config | section ^interface Vlan",
            "show running-config | include ^ip routing",
            "show cdp neighbors detail",
            "show lldp neighbors detail",
            "show running-config | section ^ip access-list",
            "show running-config | section ^interface"
        ])

        vlans = parse_vlans(
            cli_output.get("show vlan brief", "")
        )

        trunk_raw = cli_output.get("show interfaces trunk", "")
        switchport_raw = cli_output.get("show interfaces switchport", "")

        trunks = parse_trunks(trunk_raw)

        if not trunks:
            trunks = parse_switchport_trunks(switchport_raw)

        svis = parse_svis(
            cli_output.get("show ip interface brief", "")
        )

        svis = parse_svi_subnets(
            cli_output.get("show running-config | section ^interface Vlan", ""),
            svis
        )

        routing = parse_routing(
            cli_output.get("show running-config | include ^ip routing", ""),
            svis
        )

        cdp_neighbors = parse_cdp_neighbors(
            cli_output.get("show cdp neighbors detail", "")
        )

        lldp_neighbors = parse_lldp_neighbors(
            cli_output.get("show lldp neighbors detail", "")
        )

        neighbors = cdp_neighbors + lldp_neighbors

        existing_acls = parse_existing_acls(
            cli_output.get("show running-config | section ^ip access-list", "")
        )

        acl_applications = parse_acl_applications(
            cli_output.get("show running-config | section ^interface", "")
        )

        result = {
            "ip": device["ip"],
            "hostname": clean_hostname(facts.get("hostname") or device.get("hostname")),
            "model": facts.get("model") or device.get("model", ""),
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
            "acl_applications": acl_applications,
            "username": device["username"],
            "password": device["password"],
            "secret": device.get("secret"),
            "reachable": True
        }

        print(f"[OK] Device discovered: {result['hostname']} ({device['ip']})")
        print(f"[TRUNKS PARSED] {result['hostname']}: {trunks}")
        print(f"[ACL APPLICATIONS] {result['hostname']}: {acl_applications}")
        print(f"[ROUTING] {result['hostname']}: {routing}")

        if logger:
            logger.info(f"{device['ip']} discovered successfully")

        return result

    except Exception as e:
        print(f"[ERROR] Discovery failed for {device.get('ip')}: {e}")

        if logger:
            logger.error(f"{device.get('ip')} connection failed: {e}")

        return {
            "ip": device["ip"],
            "hostname": clean_hostname(device.get("hostname", "unknown")),
            "model": device.get("model", ""),
            "vendor": device.get("vendor", ""),
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
            "acl_applications": [],
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


def classify_neighbor(neighbor: dict) -> str:
    """
    SWITCH / ROUTER  -> explored with NAPALM IOS
    FIREWALL/pfSense -> detected only, not explored with NAPALM IOS
    """
    explicit_role = (neighbor.get("role") or "").upper()
    if explicit_role in ["SWITCH", "ROUTER", "FIREWALL"]:
        return explicit_role

    hostname = (neighbor.get("neighbor_hostname") or "").lower()
    platform = (neighbor.get("platform") or "").lower()
    text = f"{hostname} {platform}"

    firewall_keywords = [
        "pfsense",
        "netgate",
        "freebsd",
        "opnsense",
        "firewall"
    ]

    router_keywords = [
        "router",
        "2811",
        "1921",
        "2901",
        "2911",
        "1941",
        "4331",
        "r1",
        "r-"
    ]

    switch_keywords = [
        "switch",
        "catalyst",
        "2960",
        "3560",
        "3750",
        "4500",
        "6500",
        "iosv",
        "vios",
        "sw-"
    ]

    if any(x in text for x in firewall_keywords):
        return "FIREWALL"

    if any(x in text for x in router_keywords):
        return "ROUTER"

    if any(x in text for x in switch_keywords):
        return "SWITCH"

    # CDP peut retourner seulement "Cisco" pour les switchs/routeurs
    if "cisco" in text:
        if hostname.startswith(("r", "router")):
            return "ROUTER"
        return "SWITCH"

    return "UNKNOWN"


def should_explore_neighbor(neighbor: dict) -> bool:
    role = classify_neighbor(neighbor)
    return role in ["SWITCH", "ROUTER"]




def _read_channel_output(channel, wait_time=0.4, max_wait=6):
    output = ""
    start_time = time.time()

    while time.time() - start_time < max_wait:
        time.sleep(wait_time)

        while channel.recv_ready():
            output += channel.recv(65535).decode(errors="ignore")
            start_time = time.time()

        if output and not channel.recv_ready():
            break

    return output


def ssh_run_command(host, username, password, command, timeout=12):
    """
    Execute a command on pfSense/FreeBSD using Paramiko SSH.

    pfSense often opens the text menu after SSH login instead of a direct shell.
    This function uses an interactive shell, sends option 8 to enter the shell
    when the menu is detected, then runs the requested command.
    """
    if paramiko is None:
        raise RuntimeError("Paramiko is not installed. Cannot explore pfSense via SSH.")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            username=username,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False
        )

        channel = client.invoke_shell(width=200, height=80)
        time.sleep(1)
        initial_output = _read_channel_output(channel, wait_time=0.3, max_wait=3)

        if "Enter an option" in initial_output or "Welcome to pfSense" in initial_output:
            channel.send("8\n")
            time.sleep(1)
            _read_channel_output(channel, wait_time=0.3, max_wait=3)

        channel.send(command + "\n")
        time.sleep(1)
        output = _read_channel_output(channel, wait_time=0.4, max_wait=timeout)

        lines = output.splitlines()
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped == command.strip():
                continue

            if stripped.startswith("Enter an option"):
                continue

            if "@pfSense" in stripped and stripped.endswith("#"):
                continue

            if "@pfSense" in stripped and stripped.endswith(":"):
                continue

            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines).strip()

        if cleaned:
            return cleaned

        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exec_output = stdout.read().decode(errors="ignore")
        exec_error = stderr.read().decode(errors="ignore")

        return exec_output or exec_error

    finally:
        try:
            client.close()
        except Exception:
            pass

def _netmask_to_prefix(mask: str):
    """
    Convert FreeBSD netmask format to CIDR prefix.
    Supports:
    - 255.255.255.252
    - 0xfffffffc
    """
    if not mask:
        return None

    mask = mask.strip()

    try:
        if mask.lower().startswith("0x"):
            value = int(mask, 16)
            dotted = ".".join(str((value >> shift) & 0xff) for shift in [24, 16, 8, 0])
            return ipaddress.IPv4Network(f"0.0.0.0/{dotted}").prefixlen

        return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen

    except Exception:
        return None


def parse_pfsense_ifconfig(output: str) -> dict:
    """
    Parse pfSense/FreeBSD ifconfig output and return interfaces with IPv4 data.

    Example output:
      em0: flags=...
          inet 10.0.0.2 netmask 0xfffffffc broadcast 10.0.0.3
      em1: flags=...
          inet 192.168.99.254 netmask 0xffffff00 broadcast 192.168.99.255

    Return:
      {
        "em0": {"ip": "10.0.0.2", "prefix": 30, "network": "10.0.0.0/30"},
        "em1": {"ip": "192.168.99.254", "prefix": 24, "network": "192.168.99.0/24"}
      }
    """
    interfaces = {}
    current_interface = None

    if not output:
        return interfaces

    for raw_line in output.splitlines():
        line = raw_line.rstrip()

        int_match = re.match(r"^([A-Za-z0-9_\.:-]+):\s+flags=", line)
        if int_match:
            current_interface = int_match.group(1).strip()
            interfaces.setdefault(current_interface, {})
            continue

        if not current_interface:
            continue

        inet_match = re.search(
            r"\binet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+([^\s]+)",
            line
        )

        if inet_match:
            ip_addr = inet_match.group(1).strip()
            mask = inet_match.group(2).strip()
            prefix = _netmask_to_prefix(mask)

            interfaces[current_interface]["ip"] = ip_addr
            interfaces[current_interface]["prefix"] = prefix

            if prefix is not None:
                try:
                    network = ipaddress.ip_interface(f"{ip_addr}/{prefix}").network
                    interfaces[current_interface]["network"] = str(network)
                except Exception:
                    interfaces[current_interface]["network"] = None

    return interfaces


def _infer_point_to_point_neighbor(local_interface: str, interfaces: dict):
    """
    Infer the opposite host on a point-to-point WAN subnet.
    Safe behavior: infer only for /30 or /31 networks.
    """
    if not local_interface or local_interface not in interfaces:
        return None

    info = interfaces.get(local_interface) or {}
    ip_addr = info.get("ip")
    prefix = info.get("prefix")

    if not ip_addr or prefix not in [30, 31]:
        return None

    try:
        iface = ipaddress.ip_interface(f"{ip_addr}/{prefix}")
        hosts = [str(h) for h in iface.network.hosts()]

        for host in hosts:
            if host != str(iface.ip):
                return host

    except Exception:
        return None

    return None


def parse_pfsense_lldp_neighbors(output: str, firewall_interfaces: dict = None) -> list:
    """
    Parse lldpcli output from pfSense/FreeBSD.

    This parser supports the pfSense lldpd format:

      Interface: em0, via: LLDP, RID: 2
        Chassis:
          SysName: R1
          MgmtIP: 10.0.0.1
          Capability: Router, on
        Port:
          PortID: ifname GigabitEthernet1/0
          PortDescr: GigabitEthernet1/0

    Important:
    Some routers advertise no SysName and no MgmtIP.
    If the LLDP neighbor is on a /30 or /31 pfSense interface,
    NetAutoAI infers the neighbor IP from the point-to-point subnet.
    Example: pfSense em0 = 10.0.0.2/30 -> router = 10.0.0.1
    """
    neighbors = []
    firewall_interfaces = firewall_interfaces or {}

    if not output:
        return neighbors

    blocks = re.split(r"\n(?=Interface:\s+)", output)

    for block in blocks:
        hostname = None
        ip_addr = None
        platform = None
        local_interface = None
        remote_interface = None
        capability = None

        for raw_line in block.splitlines():
            line = raw_line.strip()

            int_match = re.match(r"^Interface:\s+([^,\s]+)", line, re.IGNORECASE)
            if int_match:
                local_interface = int_match.group(1).strip()
                continue

            sys_match = re.match(r"^(SysName|System Name):\s+(.+)", line, re.IGNORECASE)
            if sys_match:
                hostname = sys_match.group(2).strip()
                continue

            descr_match = re.match(r"^(SysDescr|System Description):\s+(.+)", line, re.IGNORECASE)
            if descr_match:
                platform = descr_match.group(2).strip()
                continue

            cap_match = re.match(r"^Capability:\s+(.+)", line, re.IGNORECASE)
            if cap_match:
                capability = cap_match.group(1).strip()
                continue

            port_match = re.match(r"^(PortID|Port id):\s+(.+)", line, re.IGNORECASE)
            if port_match:
                remote_interface = port_match.group(2).strip()
                remote_interface = re.sub(r"^ifname\s+", "", remote_interface, flags=re.IGNORECASE).strip()
                continue

            port_descr_match = re.match(r"^(PortDescr|Port Description):\s+(.+)", line, re.IGNORECASE)
            if port_descr_match and not remote_interface:
                remote_interface = port_descr_match.group(2).strip()
                continue

            mgmt_match = re.match(
                r"^(MgmtIP|Management Address|Management address):\s+(\d+\.\d+\.\d+\.\d+)",
                line,
                re.IGNORECASE
            )
            if mgmt_match:
                ip_addr = mgmt_match.group(2).strip()
                continue

            ip_match = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", line)
            if ip_match and any(x in line.lower() for x in ["mgmt", "management"]):
                ip_addr = ip_match.group(1).strip()

        # If the router does not advertise a management IP,
        # infer it from pfSense point-to-point WAN interface.
        inferred_ip = None
        if not ip_addr:
            inferred_ip = _infer_point_to_point_neighbor(local_interface, firewall_interfaces)
            if inferred_ip:
                ip_addr = inferred_ip

        # If the router does not advertise a SysName, give it a stable name.
        cap_text = (capability or platform or "").lower()
        if not hostname and "router" in cap_text:
            hostname = "R1"

        final_platform = platform or capability or "LLDP Neighbor"

        # Role detection based on pfSense LLDP information.
        # Priority rule:
        # - Hostnames starting with SW- are switches, even if they advertise Router capability
        #   because a Layer 3 switch can advertise Router capability via LLDP.
        # - Real routers are detected from Router capability or router-like hostname.
        role = "UNKNOWN"
        hostname_text = (hostname or "").lower()
        capability_text = (capability or "").lower()
        platform_text = (platform or "").lower()
        combined_text = f"{hostname_text} {capability_text} {platform_text}"

        if hostname_text.startswith("sw-") or "switch" in hostname_text:
            role = "SWITCH"
            final_platform = "SWITCH"

        elif "bridge" in capability_text and not "router" in hostname_text:
            role = "SWITCH"
            final_platform = final_platform or "SWITCH"

        elif "router" in combined_text or hostname_text.startswith(("r-", "r1", "router")):
            role = "ROUTER"
            final_platform = "ROUTER"

        if hostname or local_interface or remote_interface or ip_addr:
            neighbors.append({
                "neighbor_hostname": clean_hostname(hostname or "UNKNOWN_LLDP_NEIGHBOR"),
                "neighbor_ip": ip_addr,
                "platform": final_platform,
                "role": role,
                "local_interface": local_interface,
                "remote_interface": remote_interface,
                "protocol": "LLDP",
                "inferred_ip": bool(inferred_ip)
            })

    return neighbors


def parse_pfsense_default_gateway(route_output: str, netstat_output: str = ""):
    """
    Extract default gateway IP from pfSense/FreeBSD route output.

    Note: this is only a fallback. LLDP neighbors are preferred.
    """
    combined = f"{route_output or ''}\n{netstat_output or ''}"

    gateway_match = re.search(
        r"gateway:\s*(\d+\.\d+\.\d+\.\d+)",
        combined,
        re.IGNORECASE
    )
    if gateway_match:
        return gateway_match.group(1)

    for line in combined.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split()

        if len(parts) >= 2 and parts[0].lower() in ["default", "0.0.0.0"]:
            candidate = parts[1]
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except Exception:
                continue

    return None


def _gateway_on_small_wan_subnet(gateway_ip: str, interfaces: dict) -> bool:
    """
    Accept default gateway fallback only if it belongs to a small point-to-point subnet.
    This avoids adding wrong gateways such as the NetAutoAI VM on the LAN.
    """
    if not gateway_ip:
        return False

    try:
        gw = ipaddress.ip_address(gateway_ip)
    except Exception:
        return False

    for _iface, info in (interfaces or {}).items():
        network = info.get("network")
        prefix = info.get("prefix")

        if not network or prefix not in [30, 31]:
            continue

        try:
            if gw in ipaddress.ip_network(network, strict=False):
                return True
        except Exception:
            continue

    return False


def build_wan_router_neighbor(gateway_ip: str) -> dict:
    return {
        "neighbor_hostname": "R1",
        "neighbor_ip": gateway_ip,
        "platform": "Cisco Router / WAN Gateway",
        "local_interface": "WAN",
        "remote_interface": "UNKNOWN",
        "protocol": "WAN_ROUTE"
    }


def discover_firewall_device(firewall_seed: dict, logger=None) -> dict:
    """
    Discover pfSense as a managed firewall through SSH.

    The goal is to:
    - show pfSense LLDP neighbors in the topology
    - discover R1 from pfSense LLDP neighbors
    - infer the router IP from WAN /30 or /31 when LLDP has no MgmtIP
    - avoid adding wrong LAN default gateways
    """
    firewall = build_unmanaged_firewall(firewall_seed)

    firewall_ip = firewall_seed.get("neighbor_ip") or firewall_seed.get("ip")
    username = firewall_seed.get("username")
    password = firewall_seed.get("password")

    firewall["ip"] = firewall_ip
    firewall["username"] = username or ""
    firewall["password"] = password or ""
    firewall["secret"] = firewall_seed.get("secret")

    if not firewall_ip or not username or not password:
        firewall["managed"] = False
        firewall["reachable"] = True
        firewall["error"] = "pfSense SSH credentials not provided"
        return firewall

    try:
        ifconfig_output = ""
        try:
            ifconfig_output = ssh_run_command(
                firewall_ip,
                username,
                password,
                "ifconfig"
            )
        except Exception:
            ifconfig_output = ""

        firewall_interfaces = parse_pfsense_ifconfig(ifconfig_output)

        lldp_output = ""
        for command in [
            "lldpcli show neighbors details",
            "lldpcli show neighbors",
            "/usr/local/sbin/lldpcli show neighbors details",
            "/usr/local/sbin/lldpcli show neighbors"
        ]:
            try:
                lldp_output = ssh_run_command(
                    firewall_ip,
                    username,
                    password,
                    command
                )

                if lldp_output and "not found" not in lldp_output.lower():
                    break

            except Exception:
                continue

        lldp_neighbors = parse_pfsense_lldp_neighbors(
            lldp_output,
            firewall_interfaces=firewall_interfaces
        )

        route_output = ""
        netstat_output = ""

        try:
            route_output = ssh_run_command(
                firewall_ip,
                username,
                password,
                "route -n get default"
            )
        except Exception:
            route_output = ""

        try:
            netstat_output = ssh_run_command(
                firewall_ip,
                username,
                password,
                "netstat -rn"
            )
        except Exception:
            netstat_output = ""

        default_gateway = parse_pfsense_default_gateway(
            route_output,
            netstat_output
        )

        neighbors = []

        for item in lldp_neighbors:
            neighbors.append(item)

        # Fallback: add default gateway only if it is on a /30 or /31 interface.
        # This avoids adding 192.168.99.100 when pfSense default route points to the VM.
        if default_gateway and _gateway_on_small_wan_subnet(default_gateway, firewall_interfaces):
            gateway_already_known = any(
                n.get("neighbor_ip") == default_gateway
                for n in neighbors
            )

            if not gateway_already_known:
                neighbors.append(
                    build_wan_router_neighbor(default_gateway)
                )

        firewall["neighbors"] = neighbors
        firewall["managed"] = True
        firewall["reachable"] = True
        firewall["routing"] = bool(default_gateway)
        firewall["default_gateway"] = default_gateway
        firewall["interfaces"] = firewall_interfaces
        firewall["lldp_raw"] = lldp_output
        firewall["ifconfig_raw"] = ifconfig_output
        firewall["route_raw"] = route_output
        firewall["netstat_raw"] = netstat_output

        print(f"[OK] Firewall discovered: {firewall['hostname']} ({firewall_ip})")
        print(f"[FIREWALL INTERFACES] {firewall['hostname']}: {firewall_interfaces}")
        print(f"[FIREWALL NEIGHBORS] {firewall['hostname']}: {neighbors}")

        if logger:
            logger.info(f"[OK] Firewall discovered: {firewall_ip}")

        return firewall

    except Exception as e:
        firewall["managed"] = False
        firewall["reachable"] = True
        firewall["neighbors"] = []
        firewall["error"] = str(e)

        print(f"[WARN] Firewall detected but not explored: {firewall_ip} - {e}")

        if logger:
            logger.warning(f"Firewall detected but not explored: {firewall_ip} - {e}")

        return firewall


def build_unmanaged_firewall(neighbor: dict) -> dict:
    return {
        "ip": neighbor.get("neighbor_ip"),
        "hostname": clean_hostname(neighbor.get("neighbor_hostname") or "pfSense"),
        "model": neighbor.get("platform") or "pfSense",
        "vendor": "pfSense",
        "role": "FIREWALL",
        "managed": False,
        "reachable": True,

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
        "acl_applications": [],

        # Ces champs gardent le lien avec le switch qui l'a détecté
        "detected_by_protocol": neighbor.get("protocol"),
        "local_interface": neighbor.get("local_interface"),
        "remote_interface": neighbor.get("remote_interface")
    }


def discover_devices(seed_devices, logger=None) -> list:
    results = []
    visited_ips = set()
    detected_unmanaged_ips = set()
    queue = deque(seed_devices)

    while queue:
        current = queue.popleft()
        current_ip = current.get("ip")

        if not current_ip:
            continue

        if current_ip in visited_ips:
            continue

        visited_ips.add(current_ip)

        print(f"[DISCOVERY] Exploring {current_ip}")

        if logger:
            logger.info(f"[DISCOVERY] Exploring {current_ip}")

        discovered = discover_one_device(current, logger=logger)
        results.append(discovered)

        if not discovered.get("reachable"):
            continue

        neighbors = discovered.get("neighbors", [])

        for neighbor in neighbors:
            print(f"[{neighbor.get('protocol', 'UNKNOWN')} Neighbor Found]:", neighbor)

            neighbor_ip = neighbor.get("neighbor_ip")

            if not neighbor_ip:
                continue

            role = classify_neighbor(neighbor)

            if role == "FIREWALL":
                if neighbor_ip not in visited_ips and neighbor_ip not in detected_unmanaged_ips:
                    firewall_seed = {
                        **neighbor,
                        "ip": neighbor_ip,

                        # Identifiants SSH pfSense
                        # Ces identifiants sont séparés des identifiants Cisco.
                        "username": current.get("pfsense_username", "admin"),
                        "password": current.get("pfsense_password", "pfsense"),
                        "secret": current.get("pfsense_secret", current.get("pfsense_password", "pfsense"))
                    }

                    firewall = discover_firewall_device(
                        firewall_seed,
                        logger=logger
                    )

                    results.append(firewall)
                    detected_unmanaged_ips.add(neighbor_ip)

                    print(f"[DETECTED FIREWALL] {firewall['hostname']} ({neighbor_ip}) detected and processed")

                    if logger:
                        logger.info(f"[DETECTED FIREWALL] {neighbor_ip} detected and processed")

                    # Process pfSense neighbors to discover the WAN router.
                    # Example: pfSense default route -> 10.0.0.1 -> R1
                    for fw_neighbor in firewall.get("neighbors", []):
                        fw_neighbor_ip = fw_neighbor.get("neighbor_ip")

                        if not fw_neighbor_ip:
                            continue

                        if fw_neighbor_ip in visited_ips:
                            continue

                        fw_role = fw_neighbor.get("role") or classify_neighbor(fw_neighbor)

                        if fw_role not in ["SWITCH", "ROUTER"]:
                            print("[SKIP] Firewall neighbor ignored:", fw_neighbor)
                            continue

                        print(f"[QUEUE] Adding {fw_role} from FIREWALL:", fw_neighbor_ip)

                        queue.append({
                            "hostname": fw_neighbor.get("neighbor_hostname"),
                            "ip": fw_neighbor_ip,
                            "username": current["username"],
                            "password": current["password"],
                            "secret": current.get("secret") or current.get("password"),
                            "model": fw_neighbor.get("platform") or "ios",
                            "vendor": "Cisco",
                            "role": fw_role
                        })

                continue

            if role not in ["SWITCH", "ROUTER"]:
                print("[SKIP] Neighbor ignored:", neighbor)
                continue

            if neighbor_ip in visited_ips:
                continue

            print(f"[QUEUE] Adding {role}:", neighbor_ip)

            queue.append({
                "hostname": neighbor.get("neighbor_hostname"),
                "ip": neighbor_ip,
                "username": current["username"],
                "password": current["password"],
                "secret": current.get("secret") or current.get("password"),
                "model": neighbor.get("platform") or "ios",
                "vendor": "Cisco",
                "role": role
            })

    print("[DISCOVERY FINISHED] Total devices:", len(results))
    return results