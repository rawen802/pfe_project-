import ipaddress
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def find_project_root() -> Path:
    current = Path(__file__).resolve()

    for parent in [current.parent] + list(current.parents):
        if (parent / "app").exists():
            return parent

    return Path.cwd()


def subnet_to_cisco_parts(subnet: str):
    if str(subnet).strip().lower() == "any":
        return "any", ""

    net = ipaddress.ip_network(subnet, strict=False)
    network = str(net.network_address)
    wildcard = ".".join(str(255 - int(x)) for x in str(net.netmask).split("."))
    return network, wildcard


def enrich_rule_for_cisco(rule: dict):
    src_network, src_wildcard = subnet_to_cisco_parts(rule["source"])
    dst_network, dst_wildcard = subnet_to_cisco_parts(rule["destination"])

    enriched = dict(rule)
    enriched["source_network"] = src_network
    enriched["source_wildcard"] = src_wildcard
    enriched["destination_network"] = dst_network
    enriched["destination_wildcard"] = dst_wildcard

    if enriched.get("protocol") == "any":
        enriched["protocol"] = "ip"

    return enriched


def build_acl_device_map(acl_result: dict):
    device_map = {}

    for section in ["created", "updated", "deleted"]:
        for acl in acl_result.get(section, []):
            hostname = acl.get("device")
            if not hostname:
                continue

            if hostname not in device_map:
                device_map[hostname] = {
                    "created": [],
                    "updated": [],
                    "deleted": []
                }

            acl_copy = dict(acl)

            if section == "created":
                acl_copy["rules"] = [
                    enrich_rule_for_cisco(rule)
                    for rule in acl.get("rules", [])
                ]

            elif section == "updated":
                acl_copy["new_rules"] = [
                    enrich_rule_for_cisco(rule)
                    for rule in acl.get("new_rules", [])
                ]

            device_map[hostname][section].append(acl_copy)

    return device_map


def render_acl_configs_per_device(acl_result: dict, template_folder: str | None = None):
    base_dir = find_project_root()

    if template_folder is None:
        template_dir = base_dir / "templates"
    else:
        template_dir = Path(template_folder)

    template_file = template_dir / "ACL.j2"

    if not template_file.exists():
        raise FileNotFoundError(f"Template ACL introuvable: {template_file}")

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("ACL.j2")

    device_map = build_acl_device_map(acl_result)

    rendered = {}

    for hostname, data in device_map.items():
        rendered[hostname] = template.render(
            hostname=hostname,
            data=data
        )

    return rendered


def save_acl_configs_to_files(rendered_configs: dict, output_folder: str | None = None):
    base_dir = find_project_root()

    if output_folder is None:
        output_path = base_dir / "output" / "acl_configs"
    else:
        output_path = Path(output_folder)

    output_path.mkdir(parents=True, exist_ok=True)

    saved_files = {}

    for hostname, config_text in rendered_configs.items():
        file_path = output_path / f"{hostname}_acl.cfg"
        file_path.write_text(config_text, encoding="utf-8")
        saved_files[hostname] = str(file_path)

    return saved_files