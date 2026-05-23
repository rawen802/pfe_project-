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


def build_device_config_map(vlan_result: dict, vlsm_result: dict | None = None):
    device_map = {}
    vlsm_map = build_vlsm_map(vlsm_result or {})

    for vlan in vlan_result.get("created", []):
        vlan_id = vlan["vlan_id"]
        vlan_name = vlan["vlan_name"]
        zone_name = vlan["zone_name"]

        # Access / Distribution
        for device in vlan.get("deploy_on", []):
            hostname = device["hostname"]
            role = device.get("role", "UNKNOWN")

            if hostname not in device_map:
                device_map[hostname] = {
                    "role": role,
                    "vlans": [],
                    "trunks": defaultdict(set),
                    "svis": [],
                    "default_gateway": None
                }

            device_map[hostname]["vlans"].append({
                "vlan_id": vlan_id,
                "vlan_name": vlan_name
            })

            for trunk in device.get("trunks", []):
                device_map[hostname]["trunks"][trunk].add(vlan_id)

            # Si c'est un switch L2, on peut poser seulement ip default-gateway
            if vlan.get("needs_svi") and zone_name in vlsm_map and is_l2_role(role):
                # on ne définit qu'une seule default gateway globale par équipement
                if device_map[hostname]["default_gateway"] is None:
                    device_map[hostname]["default_gateway"] = vlsm_map[zone_name]["gateway"]

        # Core
        for core in vlan.get("core_switches", []):
            hostname = core["hostname"]
            role = core.get("role", "UNKNOWN")

            if hostname not in device_map:
                device_map[hostname] = {
                    "role": role,
                    "vlans": [],
                    "trunks": defaultdict(set),
                    "svis": [],
                    "default_gateway": None
                }

            device_map[hostname]["vlans"].append({
                "vlan_id": vlan_id,
                "vlan_name": vlan_name
            })

            # Si c'est un équipement L3, on crée le SVI avec l'IP gateway
            if vlan.get("needs_svi") and zone_name in vlsm_map and is_l3_role(role):
                ip_data = vlsm_map[zone_name]

                device_map[hostname]["svis"].append({
                    "vlan_id": vlan_id,
                    "zone_name": zone_name,
                    "interface_ip": ip_data["gateway"],
                    "mask": ip_data["mask"],
                    "subnet": ip_data["subnet"]
                })

    # Normalisation
    normalized = {}

    for hostname, data in device_map.items():
        vlans = sorted(
            {(v["vlan_id"], v["vlan_name"]) for v in data["vlans"]},
            key=lambda x: x[0]
        )

        svis = sorted(
            {(s["vlan_id"], s["zone_name"], s["interface_ip"], s["mask"], s["subnet"]) for s in data["svis"]},
            key=lambda x: x[0]
        )

        normalized[hostname] = {
            "role": data["role"],
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

        src_if = link.get("source_interface")
        dst_if = link.get("target_interface")

        if not src or not dst or not src_if or not dst_if:
            continue

        # Initialisation
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

    for item in final_plan:
        if hasattr(item, "dict"):
            item = item.dict()

        device = item.get("svi") or item.get("switches") or "CORE-SW"

        vlan_id = item.get("vlan_id")
        vlan_name = item.get("vlan_name")
        gateway = item.get("gateway")
        mask = item.get("mask")
        trunk = item.get("trunk")

        if device not in configs:
            configs[device] = {
                "lines": [
                    "! =========================================",
                    f"! DEVICE: {device}",
                    "! ROLE: SITE_CORE",
                    "! =========================================",
                    "",
                    "! -------- VLAN CREATION --------"
                ],
                "trunk_vlans": set()
            }

        configs[device]["lines"].append(f"vlan {vlan_id}")
        configs[device]["lines"].append(f" name {vlan_name}")
        configs[device]["lines"].append("!")

        if str(trunk).lower() in ["oui", "yes", "true", "1"]:
            configs[device]["trunk_vlans"].add(str(vlan_id))

        # SVI
        if gateway and mask and gateway != "-" and mask != "-":
            configs[device]["lines"].append("")
            configs[device]["lines"].append(f"interface Vlan{vlan_id}")
            configs[device]["lines"].append(f" description Gateway for {vlan_name}")
            configs[device]["lines"].append(f" ip address {gateway} {mask}")
            configs[device]["lines"].append(" no shutdown")
            configs[device]["lines"].append("!")

    # 🔥 TRUNK CONFIG basé sur la topologie
    rendered = {}

    for device, data in configs.items():
        lines = data["lines"]
        trunk_vlans = sorted(data["trunk_vlans"], key=lambda x: int(x))

        lines.append("")
        lines.append("! -------- TRUNK CONFIG --------")

        interfaces = trunk_map.get(device, [])

        if interfaces and trunk_vlans:
            vlan_list = ",".join(trunk_vlans)

            for iface in interfaces:
                lines.append(f"interface {iface}")
                lines.append(" description Auto trunk")
                lines.append(" switchport mode trunk")
                lines.append(f" switchport trunk allowed vlan add {vlan_list}")
                lines.append(" no shutdown")
                lines.append("!")

        else:
            lines.append("! No trunk detected")

        rendered[device] = "\n".join(lines)

    return rendered
