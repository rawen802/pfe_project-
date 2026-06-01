import sqlite3
from datetime import datetime
import json
from passlib.hash import bcrypt
import os

import sys

def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


BASE_DIR = get_app_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

DATABASE_NAME = os.path.join(DATA_DIR, "network_app.db")


# =========================
# Connexion DB
# =========================
def connect_db():
    print("DATABASE =", DATABASE_NAME)
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# Création des tables
# =========================
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_permissions (
        role_id INTEGER,
        permission_id INTEGER,
        PRIMARY KEY(role_id, permission_id),
        FOREIGN KEY(role_id) REFERENCES roles(id),
        FOREIGN KEY(permission_id) REFERENCES permissions(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role_id INTEGER,
        created_at TEXT,
        FOREIGN KEY(role_id) REFERENCES roles(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostname TEXT,
        ip TEXT,
        type TEXT,
        detected_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS links(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER,
        target_id INTEGER,
        created_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vlans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vlan_id INTEGER,
        vlan_name TEXT,
        device_id INTEGER,
        created_at TEXT,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS acls(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER,
        acl_name TEXT,
        action TEXT,
        protocol TEXT,
        source TEXT,
        destination TEXT,
        port TEXT,
        created_at TEXT,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        required_hosts INTEGER,
        created_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS IP_plans(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        department_id INTEGER,
        vlan_id INTEGER,
        subnet TEXT,
        mask TEXT,
        gateway TEXT,
        broadcast TEXT,
        created_at TEXT,
        UNIQUE(department_id, subnet),
        FOREIGN KEY (department_id) REFERENCES departments(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        device_id INTEGER,
        user_id INTEGER,
        module TEXT,
        status TEXT,
        extra TEXT,
        created_at TEXT,
        FOREIGN KEY (device_id) REFERENCES devices(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        type TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_name TEXT NOT NULL,
        user_id INTEGER,
        file_path TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # =========================
    # Nouvelle table : architectures sauvegardées multi-sites
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS architecture_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        site_name TEXT NOT NULL,
        report_json TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()


# =========================
# Seed données initiales
# =========================
def seed_data(cursor):
    roles = ["admin", "engineer", "analyst", "viewer"]
    permissions = [
      "manage_users",
            "view_dashboard",
            "view_alerts",
            "view_reports",
            
            "discover_site",
            "generate_vlsm",
            "create_vlan",
            "generate_acl",
            "render_config",
            "deploy_configs",
            "deploy_acl",

            "validate_ai",

            "view_security_analytics",
            "view_general_analytics",
            "view_audit_logs",

            "generate_reports",
            "architecture_list",
            "architecture_view",
            "architecture_delete"  

    ]

    for r in roles:
        cursor.execute("INSERT OR IGNORE INTO roles (name) VALUES (?)", (r,))

    for p in permissions:
        cursor.execute("INSERT OR IGNORE INTO permissions (name) VALUES (?)", (p,))


def assign_permissions(cursor):
    mapping = {
        "admin": [

            "manage_users",
            "view_dashboard",
            "view_alerts",
            "view_reports",
            
            "discover_site",
            "generate_vlsm",
            "create_vlan",
            "generate_acl",
            "render_config",
            "deploy_configs",
            "deploy_acl",

            "validate_ai",

            "view_security_analytics",
            "view_general_analytics",
            "view_audit_logs",

            "generate_reports",
            "architecture_list",
            "architecture_view",
            "architecture_delete"

            
        ],
        "engineer": [
            "view_dashboard",
            "view_alerts",
            "view_reports",

            "discover_site",
            "generate_vlsm",
            "generate_acl",
            "create_vlan",
            "render_config",
            "deploy_configs",
            "deploy_acl",

            "validate_ai",
            "architecture_list",
            "architecture_view",
            "generate_reports",

            "view_audit_logs"
            
            
        ],
        "analyst": [
            "view_dashboard",
            "view_alerts",
            "view_security_analytics",
            "view_reports",

            "validate_ai",
            "view_audit_logs",
            
            "architecture_list",
            "architecture_view",
            "discover_site"
            

        ],
        "viewer": [
            "view_dashboard",
            "view_reports",
            "view_alerts"
        ]
    }

    for role, perms in mapping.items():
        cursor.execute("SELECT id FROM roles WHERE name = ?", (role,))
        role_row = cursor.fetchone()

        if not role_row:
            print(f"Role not found: {role}")
            continue

        role_id = role_row[0]

        for perm in perms:
            cursor.execute("SELECT id FROM permissions WHERE name = ?", (perm,))
            perm_row = cursor.fetchone()

            if not perm_row:
                print(f"Permission not found: {perm}")
                continue

            permission_id = perm_row[0]

            cursor.execute("""
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            """, (role_id, permission_id))


# =========================
# Gestion utilisateurs
# =========================
def create_user(cursor, username,email, password, role):
    hashed = bcrypt.hash(password)

    cursor.execute("SELECT id FROM roles WHERE name = ?", (role,))
    role_row = cursor.fetchone()

    if not role_row:
        raise ValueError(f"Role '{role}' not found")

    role_id = role_row[0]
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO users (username, email, password, role_id, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (username, email,  hashed, role_id, date))


def authenticate(cursor, username, password):
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        return None

    user_id = user["id"]
    hashed_password = user["password"]

    if bcrypt.verify(password, hashed_password):
        return user_id

    return None


def has_permission(cursor, user_id, permission):
    query = """
    SELECT 1
    FROM users u
    JOIN roles r ON u.role_id = r.id
    JOIN role_permissions rp ON rp.role_id = r.id
    JOIN permissions p ON p.id = rp.permission_id
    WHERE u.id = ? AND p.name = ?
    """
    cursor.execute(query, (user_id, permission))
    return cursor.fetchone() is not None


def get_users():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return users


# =========================
# Devices / VLAN / ACL
# =========================
def add_device(hostname, ip, type_device):
    conn = connect_db()
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO devices (hostname, ip, type, detected_at)
        VALUES (?, ?, ?, ?)
    """, (hostname, ip, type_device, date))

    conn.commit()

    cursor.execute("SELECT id FROM devices WHERE ip = ?", (ip,))
    device_id = cursor.fetchone()["id"]

    conn.close()
    return device_id


def add_vlan_db(vlan_id, vlan_name, device_id):
    conn = connect_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        cursor.execute("""
            SELECT id FROM vlans
            WHERE device_id = ? AND vlan_id = ?
        """, (device_id, vlan_id))

        row = cursor.fetchone()

        if row:
            cursor.execute("""
                UPDATE vlans
                SET vlan_name = ?, created_at = ?
                WHERE device_id = ? AND vlan_id = ?
            """, (vlan_name, now, device_id, vlan_id))
        else:
            cursor.execute("""
                INSERT INTO vlans (device_id, vlan_id, vlan_name, created_at)
                VALUES (?, ?, ?, ?)
            """, (device_id, vlan_id, vlan_name, now))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


def build_device_map():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, hostname FROM devices")
    rows = cursor.fetchall()
    conn.close()

    return {row["hostname"]: row["id"] for row in rows}


def save_acls(acls, device_map):
    conn = connect_db()
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    saved = 0
    errors = []

    try:
        for acl in acls:
            device_id = device_map.get(acl["device"])

            if not device_id:
                errors.append(f"Device not found: {acl['device']}")
                continue

            cursor.execute("""
                INSERT INTO acls (
                    device_id, acl_name, action, protocol, source, destination, port, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id,
                acl.get("acl_name", "UNKNOWN"),
                acl.get("action"),
                acl.get("protocol"),
                acl.get("source"),
                acl.get("destination"),
                acl.get("port"),
                date
            ))

            saved += 1

        conn.commit()

    except Exception as e:
        conn.rollback()
        errors.append(str(e))

    finally:
        conn.close()

    return {
        "saved": saved,
        "errors": errors
    }


def save_architecture(devices, links, device_map):
    conn = connect_db()
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        for device in devices:
            hostname = device.get("hostname")
            ip = device.get("ip")
            role = device.get("role", "unknown")

            if hostname in device_map:
                continue

            cursor.execute("""
                INSERT INTO devices (hostname, ip, type, detected_at)
                VALUES (?, ?, ?, ?)
            """, (hostname, ip, role, date))

            device_id = cursor.lastrowid
            device_map[hostname] = device_id

        for link in links:
            source = link.get("source")
            target = link.get("target")

            source_id = device_map.get(source)
            target_id = device_map.get(target)

            if source_id and target_id:
                cursor.execute("""
                    INSERT INTO links (source_id, target_id, created_at)
                    VALUES (?, ?, ?)
                """, (source_id, target_id, date))

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"[ERREUR SAVE ARCHITECTURE] {e}")

    finally:
        conn.close()


# =========================
# Architecture Reports multi-sites
# =========================
def save_architecture_report(user_id: int, site_name: str, report: dict):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO architecture_reports (user_id, site_name, report_json)
            VALUES (?, ?, ?)
        """, (
            user_id,
            site_name or "SITE",
            json.dumps(report, ensure_ascii=False)
        ))

        conn.commit()
        report_id = cursor.lastrowid
        return report_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()


def get_architecture_reports_by_user(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, site_name, created_at
        FROM architecture_reports
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "site_name": row["site_name"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


def get_architecture_report_by_id(report_id: int, user_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, site_name, report_json, created_at
        FROM architecture_reports
        WHERE id = ? AND user_id = ?
    """, (report_id, user_id))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "site_name": row["site_name"],
        "report": json.loads(row["report_json"]),
        "created_at": row["created_at"]
    }


def delete_architecture_report(report_id: int, user_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM architecture_reports
        WHERE id = ? AND user_id = ?
    """, (report_id, user_id))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted > 0


# =========================
# Logs / Notifications / Scores
# =========================
def add_log(action, device_id=None, user_id=None, module=None, status="INFO", extra=None):
    conn = connect_db()
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO logs (action, device_id, user_id, module, status, extra, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        action,
        device_id,
        user_id,
        module,
        status,
        json.dumps(extra, ensure_ascii=False) if extra is not None else None,
        date
    ))

    conn.commit()
    conn.close()



def get_audit_logs(limit=100):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            logs.id,
            logs.action,
            logs.device_id,
            logs.user_id,
            users.username,
            logs.module,
            logs.status,
            logs.extra,
            logs.created_at
        FROM logs
        LEFT JOIN users ON users.id = logs.user_id
        ORDER BY logs.created_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "action": row["action"],
            "device_id": row["device_id"],
            "user_id": row["user_id"],
            "username": row["username"],
            "module": row["module"],
            "status": row["status"],
            "extra": json.loads(row["extra"]) if row["extra"] else None,
            "created_at": row["created_at"]
        }
        for row in rows
    ]







def create_notification(user_id, message, notif_type):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO notifications (user_id, message, type, is_read, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        message,
        notif_type,
        0,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def save_score(user_id: int, score: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ai_scores (user_id, score)
        VALUES (?, ?)
    """, (user_id, score))

    conn.commit()
    conn.close()


def save_report_file(report_name, report_data, folder="reports"):
    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = report_name.replace(" ", "_")
    file_path = os.path.join(folder, f"{safe_name}_{timestamp}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    return file_path


def add_report(report_name, user_id, file_path):
    conn = connect_db()
    cursor = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO reports (report_name, user_id, file_path, created_at)
        VALUES (?, ?, ?, ?)
    """, (report_name, user_id, file_path, date))

    conn.commit()
    report_id = cursor.lastrowid
    conn.close()

    return report_id


# =========================
# VLSM
# =========================
def save_vlsm_to_db(vlsm_data):
    conn = connect_db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    try:
        for entry in vlsm_data:
            cursor.execute(
                "SELECT id FROM departments WHERE name = ?",
                (entry["departement"],)
            )
            row = cursor.fetchone()

            if row:
                department_id = row[0]

                cursor.execute("""
                    UPDATE departments
                    SET required_hosts = COALESCE(required_hosts, ?)
                    WHERE id = ?
                """, (
                    entry.get("usable_hosts"),
                    department_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO departments (name, required_hosts, created_at)
                    VALUES (?, ?, ?)
                """, (
                    entry["departement"],
                    entry.get("usable_hosts"),
                    now
                ))
                department_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO IP_plans (
                    department_id,
                    vlan_id,
                    subnet,
                    mask,
                    gateway,
                    broadcast,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(department_id, subnet)
                DO UPDATE SET
                    mask = excluded.mask,
                    gateway = excluded.gateway,
                    broadcast = excluded.broadcast,
                    created_at = excluded.created_at
            """, (
                department_id,
                entry["id"],
                str(entry["subnet"]),
                str(entry["mask"]),
                str(entry["gateway"]),
                str(entry["broadcast"]),
                now
            ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()

#Initialisation automatique de DB:  
def migrate_database(cursor):
    """
    Migration automatique des anciennes bases SQLite.
    """

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "email" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN email TEXT"
        )

        print("Migration OK : colonne email ajoutée")      


def init_database():
    create_tables()

    conn = connect_db()
    cursor = conn.cursor()

    seed_data(cursor)
    assign_permissions(cursor)

    # Migration users.email
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "email" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN email TEXT"
        )
        conn.commit()
        print("Migration OK : colonne email ajoutée")

    # Migration AI Scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    print("Migration OK : table ai_scores vérifiée")

    conn.commit()

    try:
        create_user(
            cursor,
            "admin",
            "admin@exemple.com",
            "admin123",
            "admin"
        )

        conn.commit()
        print("Admin user created")

    except sqlite3.IntegrityError:
        print("Admin already exists")

    conn.close()
# =========================
# Main
# =========================
if __name__ == "__main__":

    init_database()
    

    print("Base de données créée avec succès")

    