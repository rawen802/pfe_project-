from collections import defaultdict
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def build_vlsm_map(vlsm_result: dict):
    result = {}

    for item in vlsm_result.get("planned_subnets", []):
        if item.get("status") != "planned":
            continue

        result[item.get("departement")] = {
            "subnet": item.get("subnet"),
            "gateway": item.get("gateway"),
            "mask": item.get("mask"),
            "broadcast": item.get("broadcast"),
            "prefix": item.get("prefix"),
            "usable_hosts": item.get("usable_hosts")
        }

    return result


def is_l2_role(role: str) -> bool:
    return role in ["ACCESS_SWITCH", "DISTRIBUTION_SWITCH"]


def is_l3_role(role: str) -> bool:
    return role in ["SITE_CORE", "CORE", "L3_SWITCH"]


def clean_device_name(value):
    if value is None:
        return ""

    if isinstance(value, list):
        if not value:
            return ""
        value = value[0]

    if isinstance(value, dict):
        return value.get("hostname") or value.get("name") or ""

    text = str(value).strip()

    if "," in text:
        return text.split(",")[0].strip()

    return text


def build_device_config_map(vlan_result: dict, vlsm_result: dict | None = None):
    device_map = {}
    vlsm_map = build_vlsm_map(vlsm_result or {})

    for vlan in vlan_result.get("created", []):
        vlan_id = vlan["vlan_id"]
        vlan_name = vlan["vlan_name"]
        zone_name = vlan["zone_name"]

        for device in vlan.get("deploy_on", []):
            hostname = device["hostname"]
            role = device.get("role", "UNKNOWN")

            if hostname not in device_map:
                device_map[hostname] = {
                    "role": role,
                    "vlans": [],
                    "trunks": defaultdict(set),
                    "svis": [],
                    "default_gateway": None,
                    "enable_ip_routing": is_l3_role(role),
                    "trunk_encapsulation_dot1q": True
                }

            device_map[hostname]["vlans"].append({
                "vlan_id": vlan_id,
                "vlan_name": vlan_name
            })

            for trunk in device.get("trunks", []):
                device_map[hostname]["trunks"][trunk].add(vlan_id)

            if vlan.get("needs_svi") and zone_name in vlsm_map and is_l2_role(role):
                if device_map[hostname]["default_gateway"] is None:
                    device_map[hostname]["default_gateway"] = vlsm_map[zone_name]["gateway"]

        for core in vlan.get("core_switches", []):
            hostname = core["hostname"]
            role = core.get("role", "SITE_CORE")

            if hostname not in device_map:
                device_map[hostname] = {
                    "role": role,
                    "vlans": [],
                    "trunks": defaultdict(set),
                    "svis": [],
                    "default_gateway": None,
                    "enable_ip_routing": is_l3_role(role),
                    "trunk_encapsulation_dot1q": True
                }

            device_map[hostname]["vlans"].append({
                "vlan_id": vlan_id,
                "vlan_name": vlan_name
            })

            if vlan.get("needs_svi") and zone_name in vlsm_map and is_l3_role(role):
                ip_data = vlsm_map[zone_name]

                device_map[hostname]["svis"].append({
                    "vlan_id": vlan_id,
                    "zone_name": zone_name,
                    "interface_ip": ip_data["gateway"],
                    "mask": ip_data["mask"],
                    "subnet": ip_data["subnet"]
                })

    normalized = {}

    for hostname, data in device_map.items():
        vlans = sorted(
            {(v["vlan_id"], v["vlan_name"]) for v in data["vlans"]},
            key=lambda x: x[0]
        )

        svis = sorted(
            {
                (
                    s["vlan_id"],
                    s["zone_name"],
                    s["interface_ip"],
                    s["mask"],
                    s["subnet"]
                )
                for s in data["svis"]
            },
            key=lambda x: x[0]
        )

        normalized[hostname] = {
            "role": data["role"],
            "enable_ip_routing": is_l3_role(data["role"]),
            "trunk_encapsulation_dot1q": True,
            "vlans": [
                {"vlan_id": vlan_id, "vlan_name": vlan_name}
                for vlan_id, vlan_name in vlans
            ],
            "trunks": [
                {
                    "interface": interface,
                    "vlan_ids": sorted(list(vlan_ids))
                }
                for interface, vlan_ids in sorted(data["trunks"].items())
            ],
            "svis": [
                {
                    "vlan_id": vlan_id,
                    "zone_name": zone_name,
                    "interface_ip": interface_ip,
                    "mask": mask,
                    "subnet": subnet
                }
                for vlan_id, zone_name, interface_ip, mask, subnet in svis
            ],
            "default_gateway": data["default_gateway"]
        }

    return normalized


def render_network_configs_per_device(
    vlan_result: dict,
    vlsm_result: dict | None = None,
    template_folder: str = "templates"
):
    env = Environment(
        loader=FileSystemLoader(template_folder),
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("VLAN.j2")
    device_map = build_device_config_map(vlan_result, vlsm_result)

    rendered = {}

    for hostname, data in device_map.items():
        rendered[hostname] = template.render(
            hostname=hostname,
            data=data
        )

    return rendered


def save_network_configs_to_files(
    rendered_configs: dict,
    output_folder: str = "output/configs"
):
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files = {}

    for hostname, config_text in rendered_configs.items():
        file_path = output_path / f"{hostname}.cfg"
        file_path.write_text(config_text, encoding="utf-8")
        saved_files[hostname] = str(file_path)

    return saved_files


def extract_trunk_interfaces(report: dict):
    trunks = {}

    links = report.get("topology", {}).get("links", [])

    for link in links:
        src = link.get("source")
        dst = link.get("target")

        src_if = (
            link.get("source_interface")
            or link.get("local_interface")
        )

        dst_if = (
            link.get("target_interface")
            or link.get("remote_interface")
        )

        if not src or not dst or not src_if or not dst_if:
            continue

        if src not in trunks:
            trunks[src] = set()

        if dst not in trunks:
            trunks[dst] = set()

        trunks[src].add(src_if)
        trunks[dst].add(dst_if)

    return trunks


def render_config_from_final_plan(final_plan, report=None):
    configs = {}
    trunk_map = extract_trunk_interfaces(report or {})

    def ensure_device(device, role):
        if not device:
            return

        if device not in configs:
            configs[device] = {
                "role": role,
                "vlans": [],
                "svis": [],
                "trunk_vlans": set()
            }
        else:
            if is_l3_role(role):
                configs[device]["role"] = role

    for item in final_plan:
        if hasattr(item, "dict"):
            item = item.dict()

        access_device = clean_device_name(item.get("switches")) or "UNKNOWN-SW"
        core_device = clean_device_name(item.get("svi")) or "SW-CORE"

        vlan_id = item.get("vlan_id")
        vlan_name = item.get("vlan_name")
        gateway = item.get("gateway")
        mask = item.get("mask")
        trunk = item.get("trunk")

        if not vlan_id or vlan_id == "-":
            continue

        if not vlan_name or vlan_name == "-":
            vlan_name = f"VLAN_{vlan_id}"

        trunk_enabled = str(trunk).lower() in ["oui", "yes", "true", "1"]

        ensure_device(access_device, "ACCESS_SWITCH")
        configs[access_device]["vlans"].append((vlan_id, vlan_name))

        if trunk_enabled:
            configs[access_device]["trunk_vlans"].add(str(vlan_id))

        ensure_device(core_device, "SITE_CORE")
        configs[core_device]["vlans"].append((vlan_id, vlan_name))

        if trunk_enabled:
            configs[core_device]["trunk_vlans"].add(str(vlan_id))

        if gateway and mask and gateway != "-" and mask != "-":
            configs[core_device]["svis"].append({
                "vlan_id": vlan_id,
                "vlan_name": vlan_name,
                "gateway": gateway,
                "mask": mask
            })

    for device, data in configs.items():
        if data["svis"]:
            data["role"] = "SITE_CORE"

    rendered = {}

    for device, data in configs.items():
        lines = [
            "! =========================================",
            f"! DEVICE: {device}",
            f"! ROLE: {data['role']}",
            "! =========================================",
            "",
            "! -------- VLAN CREATION --------"
        ]

        seen_vlans = set()

        for vlan_id, vlan_name in data["vlans"]:
            if vlan_id in seen_vlans:
                continue

            lines.append(f"vlan {vlan_id}")
            lines.append(f" name {vlan_name}")
            lines.append("!")

            seen_vlans.add(vlan_id)

        if data["role"] == "ACCESS_SWITCH":
            access_vlans = sorted(
                {str(vlan_id) for vlan_id, vlan_name in data["vlans"]},
                key=lambda x: int(x)
            )

            if access_vlans:
                access_vlan = access_vlans[0]

                trunk_interfaces = set(trunk_map.get(device, []))

                all_interfaces = [
                    "GigabitEthernet0/0",
                    "GigabitEthernet0/1",
                    "GigabitEthernet0/2",
                    "GigabitEthernet0/3"
                ]

                access_ports = [
                    iface
                    for iface in all_interfaces
                    if iface not in trunk_interfaces
                ]

                if access_ports:
                    lines.append("")
                    lines.append("! -------- ACCESS PORTS CONFIG --------")

                    for iface in access_ports:
                        lines.append(f"interface {iface}")
                        lines.append(" description Auto access port")
                        lines.append(" switchport mode access")
                        lines.append(f" switchport access vlan {access_vlan}")
                        lines.append(" spanning-tree portfast")
                        lines.append(" no shutdown")
                        lines.append("!")

        if is_l3_role(data["role"]):
            lines.append("")
            lines.append("! -------- INTER-VLAN ROUTING --------")
            lines.append("ip routing")
            lines.append("!")

        if data["svis"]:
            lines.append("")
            lines.append("! -------- SVI / GATEWAY CONFIG --------")

            seen_svis = set()

            for svi in data["svis"]:
                if svi["vlan_id"] in seen_svis:
                    continue

                lines.append(f"interface Vlan{svi['vlan_id']}")
                lines.append(f" description Gateway for {svi['vlan_name']}")
                lines.append(f" ip address {svi['gateway']} {svi['mask']}")
                lines.append(" no shutdown")
                lines.append("!")

                seen_svis.add(svi["vlan_id"])

        lines.append("")
        lines.append("! -------- TRUNK CONFIG --------")

        trunk_vlans = sorted(data["trunk_vlans"], key=lambda x: int(x))
        interfaces = trunk_map.get(device, [])

        if interfaces and trunk_vlans:
            vlan_list = ",".join(trunk_vlans)

            for iface in sorted(interfaces):
                lines.append(f"interface {iface}")
                lines.append(" description Auto trunk")
                lines.append(" switchport trunk encapsulation dot1q")
                lines.append(" switchport mode trunk")
                lines.append(f" switchport trunk allowed vlan add {vlan_list}")
                lines.append(" no shutdown")
                lines.append("!")
        else:
            lines.append("! No trunk detected")

        rendered[device] = "\n".join(lines)

    return rendered