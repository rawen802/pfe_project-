import asyncio
import json
import requests
import os

from dotenv import load_dotenv

from app.database.database import save_score
from app.websocket.manager import send_notification


# =========================
# CONFIG GEMINI
# =========================

load_dotenv()

MODEL = "gemini-2.5-flash"

API_KEYS = [
    os.getenv("API_KEY1"),
    os.getenv("API_KEY2"),
    os.getenv("API_KEY3"),
    os.getenv("API_KEY4"),
]

def get_gemini_url():
    api_key = get_current_key()
    return f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
    raise Exception("No Gemini API keys found. Check your .env file.")

current_key_index = 0


def get_current_key():
    if current_key_index >= len(API_KEYS):
        raise Exception("All API keys exhausted")
    return API_KEYS[current_key_index]


def switch_to_next_key():
    global current_key_index
    current_key_index += 1


def get_gemini_url():
    api_key = get_current_key()
    return (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{MODEL}:generateContent?key={api_key}"
    )


# =========================
# SAFE JSON PARSER
# =========================

def safe_json_parse(response_text):
    try:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON object found")

        json_str = response_text[start:end]
        return json.loads(json_str)

    except Exception:
        return {
            "status": "ERROR",
            "summary": "Invalid JSON returned by AI",
            "issues": [
                {
                    "type": "JSON_ERROR",
                    "severity": "high",
                    "description": response_text
                }
            ],
            "recommendations": [],
            "security_score": 0,
            "fixes": []
        }


# =========================
# GEMINI CALL
# =========================

def ask_gemini(prompt):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    global current_key_index

    while current_key_index < len(API_KEYS):
        try:
            url = get_gemini_url()

            response = requests.post(
                url,
                json=payload,
                timeout=60
            )

            if response.status_code in (401, 403, 404, 429, 503):
                switch_to_next_key()
                continue

            if response.status_code != 200:
                return json.dumps({
                    "status": "ERROR",
                    "summary": "Gemini API error",
                    "issues": [
                        {
                            "type": "API_ERROR",
                            "severity": "high",
                            "description": response.text
                        }
                    ],
                    "recommendations": [],
                    "security_score": 0,
                    "fixes": []
                })

            data = response.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise Exception("No candidates returned by Gemini")

            return candidates[0]["content"]["parts"][0]["text"]

        except requests.exceptions.Timeout:
            switch_to_next_key()
            continue

        except Exception as e:
            return json.dumps({
                "status": "ERROR",
                "summary": "Gemini service unavailable",
                "issues": [
                    {
                        "type": "GEMINI_DOWN",
                        "severity": "high",
                        "description": str(e)
                    }
                ],
                "recommendations": [],
                "security_score": 0,
                "fixes": []
            })

    return json.dumps({
        "status": "ERROR",
        "summary": "Gemini service unavailable",
        "issues": [
            {
                "type": "GEMINI_DOWN",
                "severity": "high",
                "description": "All API keys exhausted or Gemini unavailable"
            }
        ],
        "recommendations": [],
        "security_score": 0,
        "fixes": []
    })


# =========================
# USER INTENT PARSER
# =========================

def parse_user_intent(user_text):
    prompt = f"""
Convert the user request into structured JSON.

User input:
"{user_text}"

Return ONLY JSON:

{{
  "goal": "",
  "allow_services": [],
  "deny_services": [],
  "priority": "security | performance | balanced"
}}
"""

    raw = ask_gemini(prompt)
    return safe_json_parse(raw)


# =========================
# SCORE CALCULATION
# =========================

def compute_score(issues):
    score = 100

    high_count = 0
    medium_count = 0
    low_count = 0

    for issue in issues:
        severity = issue.get("severity", "low").lower()

        if severity == "high":
            high_count += 1

        elif severity == "medium":
            medium_count += 1

        else:
            low_count += 1

    score -= high_count * 8
    score -= medium_count * 4
    score -= low_count * 2

    score = max(score, 5)
    score = min(score, 100)

    return int(score)


# =========================
# BUILD DISCOVERY REPORT
# =========================

def build_discovery_report(discovered_devices, site_name="SITE"):
    links = []
    vlans = []
    trunks = []
    svis = []
    acls = []
    unreachable_devices = []

    for device in discovered_devices:
        hostname = device.get("hostname")
        device_ip = device.get("ip")

        if not device.get("reachable", True):
            unreachable_devices.append({
                "hostname": hostname,
                "ip": device_ip,
                "error": device.get("error")
            })

        for neighbor in device.get("neighbors", []):
            links.append({
                "source": hostname,
                "source_ip": device_ip,
                "target": neighbor.get("neighbor_hostname"),
                "target_ip": neighbor.get("neighbor_ip"),
                "local_interface": neighbor.get("local_interface"),
                "remote_interface": neighbor.get("remote_interface"),
                "platform": neighbor.get("platform"),
                "protocol": neighbor.get("protocol")
            })

        for vlan in device.get("vlans", []):
            vlans.append({
                "device": hostname,
                "device_ip": device_ip,
                **vlan
            })

        for trunk in device.get("trunks", []):
            trunks.append({
                "device": hostname,
                "device_ip": device_ip,
                "interface": trunk
            })

        for svi in device.get("svis", []):
            svis.append({
                "device": hostname,
                "device_ip": device_ip,
                **svi
            })

        for acl in device.get("existing_acls", []):
            acls.append({
                "device": hostname,
                "device_ip": device_ip,
                **acl
            })

    return {
        "site_name": site_name,
        "summary": {
            "device_count": len(discovered_devices),
            "vlan_count": len(vlans),
            "trunk_count": len(trunks),
            "svi_count": len(svis),
            "acl_count": len(acls),
            "link_count": len(links),
            "unreachable_count": len(unreachable_devices)
        },
        "topology": {
            "devices": discovered_devices,
            "links": links
        },
        "network_context": {
            "vlans": vlans,
            "trunks": trunks,
            "svis": svis,
            "acls": acls,
            "unreachable_devices": unreachable_devices
        }
    }


# =========================
# LIGHT REPORT FOR AI
# =========================

def simplify_report_for_ai(discovery_report):
    devices = discovery_report.get("topology", {}).get("devices", [])
    safe_devices = []

    for device in devices:
        safe_devices.append({
            "hostname": device.get("hostname"),
            "ip": device.get("ip"),
            "model": device.get("model"),
            "vendor": device.get("vendor"),
            "os_version": device.get("os_version"),
            "uptime": device.get("uptime"),
            "reachable": device.get("reachable"),
            "routing": device.get("routing"),
            "interfaces_count": len(device.get("interfaces", {})),
            "vlans": device.get("vlans", []),
            "trunks": device.get("trunks", []),
            "svis": device.get("svis", []),
            "neighbors": device.get("neighbors", []),
            "existing_acls": device.get("existing_acls", []),
            "error": device.get("error")
        })

    return {
        "site_name": discovery_report.get("site_name"),
        "summary": discovery_report.get("summary", {}),
        "topology": {
            "devices": safe_devices,
            "links": discovery_report.get("topology", {}).get("links", [])
        },
        "network_context": discovery_report.get("network_context", {})
    }


# =========================
# AI ANALYSIS FROM DISCOVERY REPORT
# =========================

def validate_discovery_report_with_ai(discovery_report, user_intent):
    light_report = simplify_report_for_ai(discovery_report)

    prompt = f"""
You are a senior network security engineer.

Analyze this discovered network report and adapt your fixes based on USER INTENT.

USER INTENT:
{json.dumps(user_intent, indent=2)}

DISCOVERY REPORT:
{json.dumps(light_report, indent=2)}

Analyze:
- VLAN consistency
- duplicated VLAN IDs with different meanings
- missing VLAN gateways
- subnet conflicts
- SVI/gateway problems
- trunk risks
- ACL vulnerabilities
- overly permissive ACL rules
- missing segmentation
- topology risks
- unreachable devices
- routing problems
- missing security controls

Rules:
- Respect user intent strictly
- Allowed services must NOT be blocked
- Deny unwanted services if security priority
- Generate Cisco IOS CLI fixes when possible
- Assign severity: low, medium, high

Return ONLY JSON:

{{
  "status": "OK or ERROR",
  "summary": "",
  "issues": [
    {{
      "type": "",
      "severity": "low | medium | high",
      "description": "",
      "affected_device": "",
      "affected_vlan": "",
      "recommended_fix": ""
    }}
  ],
  "recommendations": [],
  "security_score": 0,
  "fixes": [
    {{
      "issue": "",
      "commands": [],
      "explanation": ""
    }}
  ]
}}
"""

    raw_response = ask_gemini(prompt)
    result = safe_json_parse(raw_response)


    issues = result.get("issues", [])
    result["security_score"] = compute_score(issues)
    if result.get("status") == "ERROR" and not result.get("issues"):
        result["summary"] = (
            "AI service unavailable - fallback analysis used"
        )
    return result


# =========================
# NOTIFICATION ENGINE
# =========================

def process_ai_result(result, user_id, create_notification):
    for issue in result.get("issues", []):
        severity = issue.get("severity", "low")
        msg = issue.get("description", "")

        if severity == "high":
            notification_type = "critical"
        elif severity == "medium":
            notification_type = "warning"
        else:
            notification_type = "info"

        create_notification(user_id, msg, notification_type)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                send_notification(
                    user_id,
                    msg,
                    notification_type
                )
            )
        except RuntimeError:
            print("[WebSocket] No running event loop")
        except Exception as e:
            print(f"[WebSocket Error] {e}")


# =========================
# MAIN AI AGENT FROM REPORT
# =========================

def run_ai_agent_from_report(discovery_report, user_input_text, user_id, create_notification):
    user_intent = parse_user_intent(user_input_text)

    result = validate_discovery_report_with_ai(
        discovery_report=discovery_report,
        user_intent=user_intent
    )

    score = result.get("security_score", 5)

    save_score(user_id, score)

    process_ai_result(result, user_id, create_notification)

    return {
        "intent": user_intent,
        "report_used": True,
        "analysis": result,
        "score": score
    }


# =========================
# MAIN AI AGENT FROM DISCOVERED DEVICES
# =========================

def run_ai_agent_from_discovered_devices(
    discovered_devices,
    user_input_text,
    user_id,
    create_notification,
    site_name="SITE"
):
    discovery_report = build_discovery_report(
        discovered_devices=discovered_devices,
        site_name=site_name
    )

    return run_ai_agent_from_report(
        discovery_report=discovery_report,
        user_input_text=user_input_text,
        user_id=user_id,
        create_notification=create_notification
    )


# =========================
# OLD COMPATIBILITY MODE
# =========================

def run_ai_agent(vlans, acls, devices, user_input_text, user_id, create_notification):
    discovery_report = {
        "site_name": "MANUAL_INPUT",
        "summary": {
            "device_count": len(devices),
            "vlan_count": len(vlans),
            "acl_count": len(acls)
        },
        "topology": {
            "devices": devices,
            "links": []
        },
        "network_context": {
            "vlans": vlans,
            "trunks": [],
            "svis": [],
            "acls": acls,
            "unreachable_devices": []
        }
    }

    return run_ai_agent_from_report(
        discovery_report=discovery_report,
        user_input_text=user_input_text,
        user_id=user_id,
        create_notification=create_notification
    )