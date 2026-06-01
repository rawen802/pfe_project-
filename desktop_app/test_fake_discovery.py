def build_fake_discovery_report(self):
    return {
        "site": {
            "site_name": "SITE-TEST",
            "core_device": {
                "hostname": "SW-CORE-1",
                "ip": "192.168.1.1",
                "model": "Cisco 3560",
                "role": "SITE_CORE"
            }
        },

        "topology": {
            "devices": [
                {
                    "hostname": "SW-CORE-1",
                    "ip": "192.168.1.1",
                    "role": "SITE_CORE",
                    "model": "Cisco 3560",
                    "reachable": True
                },
                {
                    "hostname": "SW-ACCESS-1",
                    "ip": "192.168.1.2",
                    "role": "ACCESS",
                    "model": "Cisco 2960",
                    "reachable": True
                },
                {
                    "hostname": "FW-CORE-01",
                    "ip": "192.168.1.254",
                    "role": "FIREWALL",
                    "model": "Cisco ASA",
                    "reachable": True
                }
            ],

            "links": [
                {
                    "source": "SW-CORE-1",
                    "target": "SW-ACCESS-1",
                    "source_ip": "192.168.1.1",
                    "target_ip": "192.168.1.2",
                    "local_interface": "Gig0/1",
                    "remote_interface": "Gig0/1",
                    "protocol": "LLDP"
                },
                {
                    "source": "SW-CORE-1",
                    "target": "FW-CORE-01",
                    "source_ip": "192.168.1.1",
                    "target_ip": "192.168.1.254",
                    "local_interface": "Gig0/2",
                    "remote_interface": "Gig0/0",
                    "protocol": "LLDP"
                }
            ]
        },

        "inventory": {
            "devices": [
                {
                    "hostname": "SW-CORE-1",
                    "ip": "192.168.1.1",
                    "model": "Cisco 3560",
                    "interfaces": [
                        {"name": "Gig0/1", "status": "up", "vlan": "trunk"},
                        {"name": "Gig0/2", "status": "up", "vlan": "trunk"}
                    ],
                    "vlans": [
                        {"vlan_id": 10, "name": "ADMIN"},
                        {"vlan_id": 20, "name": "SERVERS"},
                        {"vlan_id": 30, "name": "CAMERAS"}
                    ],
                    "existing_acls": []
                },

                {
                    "hostname": "SW-ACCESS-1",
                    "ip": "192.168.1.2",
                    "model": "Cisco 2960",
                    "interfaces": [
                        {"name": "Gig0/1", "status": "up", "vlan": "trunk"},
                        {"name": "Gig0/2", "status": "up", "vlan": 10}
                    ],
                    "vlans": [
                        {"vlan_id": 10, "name": "ADMIN"},
                        {"vlan_id": 30, "name": "CAMERAS"}
                    ],
                    "existing_acls": []
                },

                {
                    "hostname": "FW-CORE-01",
                    "ip": "192.168.1.254",
                    "model": "Cisco ASA",
                    "interfaces": [
                        {"name": "Gig0/0", "status": "up"}
                    ],
                    "existing_acls": [
                        {
                            "acl_name": "ALLOW_ALL",
                            "rules": ["permit ip any any"]
                        }
                    ]
                }
            ]
        }
    }