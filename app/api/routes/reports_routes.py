from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import os
import json

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)

from app.database.database import connect_db, add_log
from core.gestion_utilisateurs.security import require_permission

router = APIRouter(prefix="/reports", tags=["Reports"])

REPORTS_DIR = "generated_reports"


def row_to_dict(cursor, row):
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


def fetch_table(table_name: str):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        return [row_to_dict(cursor, row) for row in rows]
    except Exception:
        return []
    finally:
        conn.close()


def add_title(elements, text, styles):
    elements.append(Paragraph(text, styles["Title"]))
    elements.append(Spacer(1, 18))


def add_subtitle(elements, text, styles):
    elements.append(Paragraph(text, styles["Heading2"]))
    elements.append(Spacer(1, 10))


def add_key_value_table(elements, data):
    if not data:
        return

    table_data = [["Champ", "Valeur"]]

    for key, value in data.items():
        table_data.append([str(key), str(value)])

    table = Table(table_data, colWidths=[180, 420])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 18))


def add_data_table(elements, title, rows, styles, max_rows=50):
    add_subtitle(elements, title, styles)

    if not rows:
        elements.append(Paragraph("Aucune donnée disponible.", styles["Normal"]))
        elements.append(Spacer(1, 16))
        return

    rows = rows[:max_rows]

    headers = list(rows[0].keys())[:6]
    table_data = [headers]

    for item in rows:
        line = []
        for key in headers:
            value = str(item.get(key, ""))
            if len(value) > 45:
                value = value[:45] + "..."
            line.append(value)
        table_data.append(line)

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 10))

    elements.append(
        Paragraph(
            f"Nombre total : {len(rows)} élément(s) affiché(s).",
            styles["Normal"]
        )
    )

    elements.append(Spacer(1, 18))


@router.post("/generate-global")
def generate_global_report(
    current_user: dict = Depends(require_permission("generate_reports"))
):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        user_id = current_user["id"]
        username = current_user["username"]

        devices = fetch_table("devices")
        links = fetch_table("links")
        vlans = fetch_table("vlans")
        ip_plans = fetch_table("ip_plans")
        acls = fetch_table("acls")
        logs = fetch_table("logs")
        notifications = fetch_table("notifications")
        ai_scores = fetch_table("ai_scores")

        report_data = {
            "report_type": "GLOBAL_NETWORK_REPORT",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generated_by": {
                "user_id": user_id,
                "username": username
            },
            "summary": {
                "devices_count": len(devices),
                "links_count": len(links),
                "vlans_count": len(vlans),
                "ip_plans_count": len(ip_plans),
                "acls_count": len(acls),
                "logs_count": len(logs),
                "notifications_count": len(notifications),
                "ai_scores_count": len(ai_scores)
            },
            "sections": {
                "devices": devices,
                "links": links,
                "vlans": vlans,
                "ip_plans": ip_plans,
                "acls": acls,
                "ai_scores": ai_scores,
                "logs": logs,
                "notifications": notifications
            }
        }

        filename = f"global_report_user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join(REPORTS_DIR, filename)

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(report_data, file, indent=4, ensure_ascii=False, default=str)

        cursor.execute("""
            INSERT INTO reports (report_name, user_id, file_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            filename,
            user_id,
            file_path,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

        try:
            add_log(
                action="GENERATE_GLOBAL_REPORT",
                device_id=None,
                user_id=user_id,
                module="Reports",
                status="SUCCESS",
                extra=json.dumps({
                    "report_name": filename,
                    "file_path": file_path
                })
            )
        except Exception:
            pass

        return {
            "status": "success",
            "message": "Rapport global généré avec succès",
            "report_name": filename,
            "file_path": file_path,
            "summary": report_data["summary"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


@router.get("/list")
def list_reports(
    current_user: dict = Depends(require_permission("view_reports"))
):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, report_name, user_id, file_path, created_at
            FROM reports
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()

        reports = []

        for row in rows:
            reports.append({
                "id": row[0],
                "report_name": row[1],
                "user_id": row[2],
                "file_path": row[3],
                "created_at": row[4]
            })

        return {
            "status": "success",
            "reports": reports
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


@router.post("/export-pdf/{report_id}")
def export_report_pdf(
    report_id: int,
    current_user: dict = Depends(require_permission("generate_reports"))
):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)

        cursor.execute("""
            SELECT id, report_name, file_path
            FROM reports
            WHERE id = ?
        """, (report_id,))

        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Rapport introuvable")

        report_name = row[1]
        json_path = row[2]

        if not os.path.exists(json_path):
            raise HTTPException(
                status_code=404,
                detail=f"Fichier JSON introuvable : {json_path}"
            )

        with open(json_path, "r", encoding="utf-8") as file:
            report_data = json.load(file)

        pdf_name = report_name.replace(".json", ".pdf")
        pdf_path = os.path.join(REPORTS_DIR, pdf_name)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25
        )

        styles = getSampleStyleSheet()
        elements = []

        add_title(elements, "Rapport Réseau Global", styles)

        elements.append(Paragraph(f"<b>Nom du rapport :</b> {report_name}", styles["Normal"]))
        elements.append(Paragraph(f"<b>Date de génération :</b> {report_data.get('generated_at', '')}", styles["Normal"]))
        elements.append(Paragraph(
            f"<b>Généré par :</b> {report_data.get('generated_by', {}).get('username', '')}",
            styles["Normal"]
        ))

        elements.append(Spacer(1, 20))

        add_subtitle(elements, "Résumé Général", styles)
        add_key_value_table(elements, report_data.get("summary", {}))

        sections = report_data.get("sections", {})

        elements.append(PageBreak())
        add_data_table(elements, "Architecture - Équipements détectés", sections.get("devices", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "Architecture - Liens réseau", sections.get("links", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "VLAN configurés", sections.get("vlans", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "Plan VLSM / Adressage IP", sections.get("ip_plans", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "ACL / Règles de sécurité", sections.get("acls", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "Analyse IA / Scores", sections.get("ai_scores", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "Logs d'audit", sections.get("logs", []), styles)

        elements.append(PageBreak())
        add_data_table(elements, "Notifications", sections.get("notifications", []), styles)

        doc.build(elements)

        try:
            add_log(
                action="EXPORT_REPORT_PDF",
                device_id=None,
                user_id=current_user.get("id"),
                module="Reports",
                status="SUCCESS",
                extra=json.dumps({
                    "report_id": report_id,
                    "pdf_path": pdf_path
                })
            )
        except Exception:
            pass

        return {
            "status": "success",
            "message": "PDF détaillé généré avec succès",
            "pdf_path": pdf_path
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()