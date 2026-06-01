import asyncio
import json
import os
import re
import time
import requests

from dotenv import load_dotenv

from app.database.database import save_score
from app.websocket.manager import send_notification


# =========================
# CONFIG GEMINI
# =========================

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

API_KEYS = [
    os.getenv("API_KEY1"),
    os.getenv("API_KEY2"),
    os.getenv("API_KEY3"),
    os.getenv("API_KEY4"),
]

API_KEYS = [key for key in API_KEYS if key]

if not API_KEYS:
    raise Exception("No Gemini API keys found. Check your .env file.")

current_key_index = 0


def get_current_key():
    global current_key_index

    if not API_KEYS:
        raise Exception("No Gemini API keys configured")

    if current_key_index >= len(API_KEYS):
        current_key_index = 0

    return API_KEYS[current_key_index]


def switch_to_next_key():
    global current_key_index

    if not API_KEYS:
        raise Exception("No Gemini API keys configured")

    current_key_index = (current_key_index + 1) % len(API_KEYS)


def get_gemini_url():
    api_key = get_current_key()

    return (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{MODEL}:generateContent?key={api_key}"
    )


# =========================
# FALLBACK RESULT
# =========================

def fallback_result(summary="AI service unavailable", description="Gemini unavailable"):
    return {
        "status": "ERROR",
        "summary": summary,
        "issues": [
            {
                "type": "GEMINI_ERROR",
                "severity": "high",
                "description": description,
                "affected_device": "",
                "affected_vlan": "",
                "recommended_fix": "Retry later or check Gemini API keys."
            }
        ],
        "recommendations": [],
        "security_score": 5,
        "fixes": []
    }


# =========================
# SAFE JSON PARSER
# =========================

def clean_ai_response(response_text):
    if not response_text:
        return ""

    text = str(response_text).strip()

    text = text.replace("```json", "")
    text = text.replace("```JSON", "")
    text = text.replace("```", "")
    text = text.strip()

    return text


def safe_json_parse(response_text):
    try:
        text = clean_ai_response(response_text)

        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)

        if not match:
            raise ValueError("No JSON object found")

        json_str = match.group(0)
        return json.loads(json_str)

    except Exception:
        return fallback_result(
            summary="Invalid JSON returned by AI",
            description=str(response_text)
        )


# =========================
# GEMINI CALL
# =========================

def ask_gemini(prompt, max_attempts=None):
    if max_attempts is None:
        max_attempts = len(API_KEYS) * 2

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }

    last_error = None

    for attempt in range(max_attempts):
        try:
            url = get_gemini_url()

            response = requests.post(
                url,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])

                if not candidates:
                    return json.dumps(
                        fallback_result(
                            summary="No response from Gemini",
                            description="No candidates returned by Gemini"
                        )
                    )

                parts = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [])
                )

                if not parts:
                    return json.dumps(
                        fallback_result(
                            summary="Invalid Gemini response",
                            description="No parts returned by Gemini"
                        )
                    )

                return parts[0].get("text", "")

            if response.status_code in (401, 403, 404, 429, 500, 503):
                last_error = f"Gemini HTTP {response.status_code}: {response.text}"
                switch_to_next_key()
                time.sleep(1)
                continue

            return json.dumps(
                fallback_result(
                    summary="Gemini API error",
                    description=response.text
                )
            )

        except requests.exceptions.Timeout:
            last_error = "Gemini request timeout"
            switch_to_next_key()
            time.sleep(1)
            continue

        except Exception as e:
            last_error = str(e)
            switch_to_next_key()
            time.sleep(1)
            continue

    return json.dumps(
        fallback_result(
            summary="Gemini service unavailable",
            description=last_error or "All API keys exhausted or Gemini unavailable"
        )
    )


# =========================
# USER INTENT PARSER
# =========================

def parse_user_intent(user_text):
    if not user_text:
        user_text = "Analyze the network and improve security."

    prompt = f"""
Convert the user request into structured JSON.

User input:
"{user_text}"

Return ONLY this JSON format:

{{
  "goal": "",
  "allow_services": [],
  "deny_services": [],
  "priority": "security"
}}
"""

    raw = ask_gemini(prompt)
    result = safe_json_parse(raw)

    if result.get("status") == "ERROR":
        return {
            "goal": user_text,
            "allow_services": [],
            "deny_services": [],
            "priority": "security"
        }

    return {
        "goal": result.get("goal", user_text),
        "allow_services": result.get("allow_services", []),
        "deny_services": result.get("deny_services", []),
        "priority": result.get("priority", "security")
    }


# =========================
# SCORE CALCULATION
# =========================

def compute_score(issues):
    score = 100

    for issue in issues:
        severity = str(issue.get("severity", "low")).lower()

        if severity == "high":
            score -= 8
        elif severity == "medium":
            score -= 4
        else:
            score -= 2

    return max(5, min(100, int(score)))


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

    if not isinstance(discovered_devices, list):
        discovered_devices = []

    for device in discovered_devices:
        if not isinstance(device, dict):
            continue

        hostname = device.get("hostname")
        device_ip = device.get("ip")

        if not device.get("reachable", True):
            unreachable_devices.append({
                "hostname": hostname,
                "ip": device_ip,
                "error": device.get("error")
            })

        for neighbor in device.get("neighbors", []):
            if not isinstance(neighbor, dict):
                continue

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
            if isinstance(vlan, dict):
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
            if isinstance(svi, dict):
                svis.append({
                    "device": hostname,
                    "device_ip": device_ip,
                    **svi
                })

        for acl in device.get("existing_acls", []):
            if isinstance(acl, dict):
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
    if not isinstance(discovery_report, dict):
        discovery_report = {}

    devices = discovery_report.get("topology", {}).get("devices", [])
    safe_devices = []

    for device in devices:
        if not isinstance(device, dict):
            continue

        interfaces = device.get("interfaces", {})

        if isinstance(interfaces, dict):
            interfaces_count = len(interfaces)
        elif isinstance(interfaces, list):
            interfaces_count = len(interfaces)
        else:
            interfaces_count = 0

        safe_devices.append({
            "hostname": device.get("hostname"),
            "ip": device.get("ip"),
            "role": device.get("role"),
            "model": device.get("model"),
            "vendor": device.get("vendor"),
            "os_version": device.get("os_version"),
            "uptime": device.get("uptime"),
            "reachable": device.get("reachable"),
            "routing": device.get("routing"),
            "interfaces_count": interfaces_count,
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
You are a senior Cisco network security engineer.

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
- Do not invent devices that are not in the report
- Keep commands safe and realistic

Return ONLY this JSON format:

{{
  "status": "OK",
  "summary": "",
  "issues": [
    {{
      "type": "",
      "severity": "low",
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

    if not isinstance(issues, list):
        issues = []
        result["issues"] = issues

    result["security_score"] = compute_score(issues)

    if not result.get("status"):
        result["status"] = "OK"

    if not result.get("summary"):
        result["summary"] = "AI analysis completed"

    if "recommendations" not in result:
        result["recommendations"] = []

    if "fixes" not in result:
        result["fixes"] = []

    return result


# =========================
# NOTIFICATION ENGINE
# =========================

def process_ai_result(result, user_id, create_notification):
    issues = result.get("issues", [])

    if not isinstance(issues, list):
        return

    for issue in issues[:10]:
        severity = str(issue.get("severity", "low")).lower()
        msg = issue.get("description", "AI issue detected")

        if severity == "high":
            notification_type = "critical"
        elif severity == "medium":
            notification_type = "warning"
        else:
            notification_type = "info"

        try:
            create_notification(user_id, msg, notification_type)
        except Exception as e:
            print(f"[Notification DB Error] {e}")

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

def run_ai_agent_from_report(
    discovery_report,
    user_input_text,
    user_id,
    create_notification
):
    user_intent = parse_user_intent(user_input_text)

    result = validate_discovery_report_with_ai(
        discovery_report=discovery_report,
        user_intent=user_intent
    )

    score = result.get("security_score", 5)

    try:
        save_score(user_id, score)
    except Exception as e:
        print(f"[Save Score Error] {e}")

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

def run_ai_agent(
    vlans,
    acls,
    devices,
    user_input_text,
    user_id,
    create_notification
):
    discovery_report = {
        "site_name": "MANUAL_INPUT",
        "summary": {
            "device_count": len(devices) if isinstance(devices, list) else 0,
            "vlan_count": len(vlans) if isinstance(vlans, list) else 0,
            "acl_count": len(acls) if isinstance(acls, list) else 0
        },
        "topology": {
            "devices": devices if isinstance(devices, list) else [],
            "links": []
        },
        "network_context": {
            "vlans": vlans if isinstance(vlans, list) else [],
            "trunks": [],
            "svis": [],
            "acls": acls if isinstance(acls, list) else [],
            "unreachable_devices": []
        }
    }

    return run_ai_agent_from_report(
        discovery_report=discovery_report,
        user_input_text=user_input_text,
        user_id=user_id,
        create_notification=create_notification
    )