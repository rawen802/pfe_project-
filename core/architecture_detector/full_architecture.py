from core.architecture_detector.discovery import discover_devices
from core.architecture_detector.detector import classify_devices
from core.architecture_detector.topology_mapper import detect_links


def infer_zone_name(vlan_id, vlan_name):
    name = (vlan_name or "").lower()

    if "admin" in name:
        return "ADMIN"
    if "prod" in name or "fabric" in name or "usine" in name:
        return "FABRICATION"
    if "camera" in name or "cam" in name or "cctv" in name:
        return "CAMERAS"
    if "server" in name or "srv" in name or "dmz" in name:
        return "SERVERS"
    if "qualite" in name:
        return "QUALITE"
    if "securite" in name:
        return "SECURITE"
    if "commercial" in name:
        return "COMMERCIAL"

    return f"VLAN_{vlan_id}" if vlan_id is not None else "UNKNOWN_ZONE"


def build_site_report(seed_device, site_name="SITE", logger=None):
    detected_devices = discover_devices([seed_device], logger=logger)

    classified_devices = classify_devices(detected_devices, logger=logger)

    topology_links = detect_links(classified_devices)

    topology_devices = []
    vlans_context = []
    subnets_context = []
    zones_context = []
    routing_devices = []
    firewalls = []
    acl_points = []

    for device in classified_devices:
        hostname = device.get("hostname")
        ip = device.get("ip")
        role = device.get("role")
        model = device.get("model")
        routing = device.get("routing", False)
        svis = device.get("svis", [])
        vlans = device.get("vlans", [])
        interfaces = device.get("interfaces", {})
        existing_acls = device.get("existing_acls", [])

        # IMPORTANT : garder les identifiants pour AI Apply Fix / Deploy
        device["username"] = seed_device.get("username")
        device["password"] = seed_device.get("password")
        device["secret"] = seed_device.get("secret") or seed_device.get("password")

        topology_devices.append({
            "hostname": hostname,
            "ip": ip,
            "role": role,
            "model": model,
            "reachable": device.get("reachable", True),
            "username": seed_device.get("username"),
            "password": seed_device.get("password"),
            "secret": seed_device.get("secret") or seed_device.get("password")
        })

        if routing:
            routing_devices.append({
                "hostname": hostname,
                "ip": ip,
                "type": "L3_SWITCH" if role in ["SITE_CORE", "DISTRIBUTION_SWITCH"] else role
            })

        if role == "FIREWALL":
            firewalls.append({
                "hostname": hostname,
                "ip": ip
            })

        for vlan in vlans:
            existing = next(
                (
                    v for v in vlans_context
                    if v["vlan_id"] == vlan.get("id")
                    and v["vlan_name"] == vlan.get("name")
                ),
                None
            )

            if existing:
                if hostname not in existing["devices"]:
                    existing["devices"].append(hostname)
            else:
                vlans_context.append({
                    "vlan_id": vlan.get("id"),
                    "vlan_name": vlan.get("name"),
                    "devices": [hostname]
                })

        for svi in svis:
            vlan_id = svi.get("vlan")
            vlan_name = svi.get("name", "")
            subnet = svi.get("subnet")
            gateway_ip = svi.get("gateway") or svi.get("ip")

            if subnet:
                subnet_item = {
                    "subnet": subnet,
                    "vlan_id": vlan_id,
                    "zone_name": infer_zone_name(vlan_id, vlan_name),
                    "gateway_device": hostname,
                    "gateway_interface": f"Vlan{vlan_id}" if vlan_id is not None else None,
                    "gateway_ip": gateway_ip
                }

                if subnet_item not in subnets_context:
                    subnets_context.append(subnet_item)

                zone_item = {
                    "zone_name": infer_zone_name(vlan_id, vlan_name),
                    "vlan_id": vlan_id,
                    "subnet": subnet,
                    "gateway_device": hostname,
                    "gateway_interface": f"Vlan{vlan_id}" if vlan_id is not None else None
                }

                if zone_item not in zones_context:
                    zones_context.append(zone_item)

        if role == "FIREWALL":
            acl_points.append({
                "device": hostname,
                "type": "FIREWALL",
                "interfaces": list(interfaces.keys()),
                "reason": "security boundary"
            })

        elif role in ["SITE_CORE", "DISTRIBUTION_SWITCH"] and routing and svis:
            acl_points.append({
                "device": hostname,
                "type": "L3_SWITCH",
                "interfaces": [
                    f"Vlan{s['vlan']}"
                    for s in svis
                    if s.get("vlan") is not None
                ],
                "reason": "inter-vlan routing"
            })

        elif role == "EDGE_ROUTER":
            acl_points.append({
                "device": hostname,
                "type": "EDGE_ROUTER",
                "interfaces": list(interfaces.keys()),
                "reason": "wan/inter-site boundary"
            })

    all_acls = []

    for device in classified_devices:
        hostname = device.get("hostname")

        for acl in device.get("existing_acls", []):
            all_acls.append({
                "device": hostname,
                "acl": acl
            })

    # ===== FIX ACL POINTS POUR AI =====
    # Si aucun point ACL n'est détecté automatiquement mais que des ACL existent,
    # on crée des points ACL à partir des ACL réellement découvertes.
    # Cela évite que l'IA conclue à tort : "No ACLs are configured".
    if not acl_points and all_acls:
        acl_points = [
            {
                "device": item["device"],
                "type": "EXISTING_ACL",
                "acl_name": (
                    item["acl"].get("name")
                    or item["acl"].get("acl_name")
                    if isinstance(item["acl"], dict)
                    else str(item["acl"])
                ),
                "reason": "existing ACL detected"
            }
            for item in all_acls
        ]
    # ================================

    summary = {
        "device_count": len(topology_devices),
        "switch_count": len([
            d for d in topology_devices
            if "SWITCH" in str(d.get("role")) or d.get("role") == "SITE_CORE"
        ]),
        "router_count": len([
            d for d in topology_devices
            if d.get("role") == "EDGE_ROUTER"
        ]),
        "firewall_count": len([
            d for d in topology_devices
            if d.get("role") == "FIREWALL"
        ]),
        "zone_count": len(zones_context),
        "vlan_count": len(vlans_context),
        "subnet_count": len(subnets_context),
        "acl_candidate_count": len(acl_points),
        "acl_count": len(all_acls)
    }

    ai_context = {
        "topology_health_inputs": {
            "device_count": len(topology_devices),
            "link_count": len(topology_links),
            "zone_count": len(zones_context),
            "routing_device_count": len(routing_devices),
            "firewall_present": len(firewalls) > 0,
            "acl_candidate_count": len(acl_points)
        },
        "consistency_inputs": {
            "zones_without_gateway": [
                z for z in zones_context
                if not z.get("gateway_device")
            ],
            "vlans_without_subnet": [
                v for v in vlans_context
                if v["vlan_id"] not in [s["vlan_id"] for s in subnets_context]
            ],
            "subnets_without_zone": [
                s for s in subnets_context
                if not s.get("zone_name")
            ],
            "isolated_devices": [
                d for d in topology_devices
                if d["hostname"] not in [l.get("source") for l in topology_links]
                and d["hostname"] not in [l.get("target") for l in topology_links]
            ]
        },
        "security_inputs": {
            "existing_acl_count": len(all_acls),
            "firewall_count": len(firewalls),
            "inter_vlan_routing": len(routing_devices) > 0
        }
    }

    report = {
        "site": {
            "site_name": site_name,
            "core_device": {
                "hostname": seed_device.get("hostname"),
                "ip": seed_device.get("ip"),
                "model": seed_device.get("model", ""),
                "role": "SITE_CORE",
                "username": seed_device.get("username"),
                "password": seed_device.get("password"),
                "secret": seed_device.get("secret") or seed_device.get("password")
            }
        },
        "summary": summary,
        "topology": {
            "devices": topology_devices,
            "links": topology_links
        },
        "inventory": {
            "devices": classified_devices
        },
        "network_context": {
            "vlans": vlans_context,
            "subnets": subnets_context,
            "zones": zones_context,
            "routing_devices": routing_devices,
            "firewalls": firewalls,
            "acl_points": acl_points,
            "acls": all_acls
        },
        "ai_context": ai_context
    }

    return report 