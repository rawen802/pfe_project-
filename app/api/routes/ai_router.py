from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from netmiko import ConnectHandler
from netmiko.exceptions import (
    ReadTimeout,
    NetmikoTimeoutException,
    NetmikoAuthenticationException
)

from app.websocket.manager import active_connections
from app.services.ai_service import run_ai_agent_from_report
from app.api.shémas import (
    AIReportRequest,
    ScoreHistoryResponse
)
from app.database.database import (
    create_notification,
    save_score,
    add_log,
    connect_db
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/validate")
def validate_discovery_report(request: AIReportRequest):
    print("REQUEST:", request.dict())

    try:
        result = run_ai_agent_from_report(
            discovery_report=request.discovery_report,
            user_input_text=request.user_input_text,
            user_id=request.user_id,
            create_notification=create_notification
        )

        print("AI RESULT:", result)

        score = result.get("score", 0)
        save_score(request.user_id, int(score))

        add_log(
            action="VALIDATE_AI",
            user_id=request.user_id,
            module="AI_SECURITY",
            status="SUCCESS",
            extra={
                "score": score,
                "message": "Discovery report analyzed successfully"
            }
        )

        return {
            "status": "success",
            "message": "Discovery report analyzed successfully",
            "data": result
        }

    except Exception as e:
        print("AI VALIDATION ERROR =", str(e))

        add_log(
            action="VALIDATE_AI",
            user_id=request.user_id,
            module="AI_SECURITY",
            status="ERROR",
            extra={"error": str(e)}
        )

        raise HTTPException(
            status_code=500,
            detail=f"AI validation error: {str(e)}"
        )


@router.post("/validate-fix")
def validate_fix(data: dict):
    confirm = data.get("confirm")

    add_log(
        action="VALIDATE_AI_FIX",
        user_id=data.get("user_id"),
        module="AI_SECURITY",
        status="APPROVED" if confirm else "REJECTED",
        extra={"confirm": confirm}
    )

    return {
        "status": "APPROVED" if confirm else "REJECTED"
    }


def is_dangerous_command(cmd: str) -> bool:
    c = cmd.strip().lower()

    forbidden_exact = [
        "no ip address",
        "shutdown",
        "reload",
        "erase startup-config",
        "erase running-config",
        "write erase",
        "delete flash:",
        "format flash:",
        "no ip ssh",
        "transport input none",
        "no username admin",
        "no vlan 1002",
        "no vlan 1003",
        "no vlan 1004",
        "no vlan 1005",
    ]

    if c in forbidden_exact:
        return True

    forbidden_prefixes = [
        "reload",
        "erase ",
        "delete ",
        "format ",
        "no username ",
        "no ip route",
        "no ip default-gateway",
    ]

    for prefix in forbidden_prefixes:
        if c.startswith(prefix):
            return True

    return False


def apply_commands_to_cisco(
    device_ip,
    username,
    password,
    commands,
    secret=None
):
    device = {
        "device_type": "cisco_ios",
        "host": device_ip,
        "username": username,
        "password": password,
        "secret": secret or password,
        "global_delay_factor": 4,
        "fast_cli": False,
        "timeout": 60,
        "conn_timeout": 30,
        "banner_timeout": 30,
        "auth_timeout": 30,
        "ssh_strict": False,
        "system_host_keys": False,
        "disabled_algorithms": {
            "pubkeys": ["rsa-sha2-256", "rsa-sha2-512"]
        },
    }

    conn = None

    try:
        print("CONNECTING TO DEVICE =", device_ip)

        conn = ConnectHandler(**device)
        print("CONNECTED SUCCESSFULLY")

        try:
            conn.enable()
        except Exception as e:
            print("ENABLE MODE WARNING =", str(e))

        prompt = conn.find_prompt()
        print("DEVICE PROMPT =", prompt)

        conn.send_command_timing("terminal length 0")

        cleaned_commands = []
        skipped_commands = []

        for cmd in commands:
            if not cmd:
                continue

            cmd = str(cmd).strip()

            if not cmd:
                continue

            if cmd.startswith("!"):
                skipped_commands.append(cmd)
                print("SKIP COMMENT =", cmd)
                continue

            if cmd.lower() in [
                "configure terminal",
                "conf t",
                "end",
                "exit"
            ]:
                continue

            if is_dangerous_command(cmd):
                skipped_commands.append(cmd)
                print("SKIP DANGEROUS =", cmd)
                continue

            cleaned_commands.append(cmd)

        if not cleaned_commands:
            raise HTTPException(
                status_code=400,
                detail="No valid Cisco commands to apply after security filtering"
            )

        print("COMMANDS TO APPLY =", cleaned_commands)
        print("SKIPPED COMMANDS =", skipped_commands)

        output = ""
        output += conn.send_command_timing("configure terminal")
        output += "\n"

        for cmd in cleaned_commands:
            print("APPLY CMD =", cmd)

            cmd_output = conn.send_command_timing(
                cmd,
                delay_factor=4,
                max_loops=1000,
                read_timeout=30
            )

            output += f"\n{prompt}(config)# {cmd}\n{cmd_output}\n"

        output += conn.send_command_timing("end")
        output += "\n"

        try:
            save_output = conn.send_command_timing(
                "write memory",
                delay_factor=4,
                max_loops=1000,
                read_timeout=30
            )

            if "confirm" in save_output.lower():
                save_output += conn.send_command_timing("\n")

            output += "\nSAVE CONFIG OUTPUT:\n" + str(save_output)

        except Exception as e:
            print("SAVE CONFIG WARNING =", str(e))
            output += f"\nSAVE CONFIG WARNING: {str(e)}"

        if skipped_commands:
            output += "\n\nSKIPPED UNSAFE COMMANDS:\n"
            for skipped in skipped_commands:
                output += f"- {skipped}\n"

        return output

    except NetmikoAuthenticationException as e:
        print("NETMIKO AUTH ERROR =", str(e))
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed on device {device_ip}: {str(e)}"
        )

    except NetmikoTimeoutException as e:
        print("NETMIKO CONNECTION TIMEOUT =", str(e))
        raise HTTPException(
            status_code=504,
            detail=f"Connection timeout to device {device_ip}: {str(e)}"
        )

    except ReadTimeout as e:
        print("NETMIKO READ TIMEOUT =", str(e))
        raise HTTPException(
            status_code=504,
            detail=f"Read timeout while applying commands on {device_ip}: {str(e)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        print("CISCO APPLY ERROR =", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Cisco configuration error on {device_ip}: {str(e)}"
        )

    finally:
        if conn:
            try:
                conn.disconnect()
                print("DISCONNECTED FROM DEVICE")
            except Exception:
                pass


@router.post("/apply-fix")
def apply_fix(data: dict):
    fixes = data.get("fixes", [])
    device = data.get("device")

    if not device:
        raise HTTPException(status_code=400, detail="Device info missing")

    required = ["ip", "username", "password"]
    missing = [k for k in required if not device.get(k)]

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing device fields: {', '.join(missing)}"
        )

    commands = []

    for fix in fixes:
        commands.extend(fix.get("commands", []))

    if not commands:
        raise HTTPException(status_code=400, detail="No fix commands provided")

    output = apply_commands_to_cisco(
        device_ip=device["ip"],
        username=device["username"],
        password=device["password"],
        secret=device.get("secret"),
        commands=commands
    )

    add_log(
        action="APPLY_AI_FIX",
        user_id=data.get("user_id"),
        module="AI_SECURITY",
        status="APPLIED",
        extra={
            "device": device["ip"],
            "fix_count": len(fixes),
            "commands": commands,
            "output": output
        }
    )

    return {
        "status": "APPLIED",
        "device": device["ip"],
        "commands": commands,
        "output": output
    }


@router.websocket("/ws/notifications/{user_id}")
async def notifications_ws(websocket: WebSocket, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        active_connections.pop(user_id, None)

    except Exception:
        active_connections.pop(user_id, None)


@router.get("/score-history/{user_id}", response_model=ScoreHistoryResponse)
def get_score_history(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute(
        """
        SELECT score, created_at
        FROM ai_scores
        WHERE user_id = ?
        ORDER BY created_at ASC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.commit()
    conn.close()

    add_log(
        action="VIEW_AI_SCORE_HISTORY",
        user_id=user_id,
        module="AI_SECURITY",
        status="SUCCESS",
        extra={"count": len(rows)}
    )

    return {
        "user_id": user_id,
        "history": [
            {
                "score": row["score"],
                "timestamp": row["created_at"]
            }
            for row in rows
        ]
    }