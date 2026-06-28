def detect_links(devices):
    
    links = []
    seen_links = set()

    for device in devices:
        source_name = device.get("hostname", device.get("ip", "unknown"))
        source_ip = device.get("ip")
        neighbors = device.get("neighbors", [])

        for neighbor in neighbors:
            target_name = neighbor.get("neighbor_hostname", "unknown")
            target_ip = neighbor.get("neighbor_ip")
            local_interface = neighbor.get("local_interface")
            remote_interface = neighbor.get("remote_interface")
            protocol = neighbor.get("protocol", "UNKNOWN")

            # évite les doublons A-B et B-A
            link_id = tuple(sorted([
                str(source_name),
                str(target_name),
                str(local_interface),
                str(remote_interface)
            ]))

            if link_id in seen_links:
                continue

            links.append({
                "source": source_name,
                "target": target_name,
                "source_ip": source_ip,
                "target_ip": target_ip,
                "local_interface": local_interface,
                "remote_interface": remote_interface,
                "protocol": protocol
            })

            seen_links.add(link_id)

    return links