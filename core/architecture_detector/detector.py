def classify_devices(devices, logger=None):

    for device in devices:
        model = (device.get("model") or "").lower()
        hostname = (device.get("hostname") or "").lower()
        interfaces = device.get("interfaces", {})
        trunks = device.get("trunks", [])
        svis = device.get("svis", [])
        routing = device.get("routing", False)
        neighbors = device.get("neighbors", [])

        int_count = len(interfaces)
        infra_neighbors = 0

        # Compter les voisins réseau 
        for neighbor in neighbors:
            platform = (neighbor.get("platform") or "").lower()

            if any(x in platform for x in [
                "switch", "catalyst",
                "router", "2811", "1921",
                "fortinet", "cyberoam", "firewall"
            ]):
                infra_neighbors += 1

        role = "UNKNOWN"

        # Firewall
        if any(x in model for x in ["fortinet", "cyberoam", "firewall"]):
            role = "FIREWALL"

        # Routeur
        elif any(x in model for x in ["2811", "1921", "router"]):
            role = "EDGE_ROUTER"

        # Switch coeur
        elif any(x in model for x in ["4500", "4506", "6500"]) or "core" in hostname:
            role = "SITE_CORE"

        elif routing and len(svis) >= 2 and infra_neighbors >= 2:
            role = "SITE_CORE"

        # Distribution
        elif len(trunks) >= 2 and infra_neighbors >= 2:
            role = "DISTRIBUTION_SWITCH"

        # Access
        elif int_count >= 24:
            role = "ACCESS_SWITCH"

        device["role"] = role

        if logger:
            logger.info(f"[CLASSIFY] {device.get('hostname', device.get('ip'))} => {role}")

    return devices