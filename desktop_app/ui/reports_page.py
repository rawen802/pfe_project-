from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt

import os
import sys
import subprocess


class ReportsPage(QWidget):

    def __init__(self, api_client, current_user):
        super().__init__()
        self.api_client = api_client
        self.current_user = current_user
        self.setup_ui()
        self.load_reports()

    def setup_ui(self):

        self.setStyleSheet("""
            QWidget {
                background-color: #0b1424;
                color: #e2e8f0;
                font-size: 14px;
                font-family: Segoe UI;
            }

            QLabel {
                color: #f8fafc;
            }

            QPushButton {
                background-color: #1e3a5f;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px 18px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #2563eb;
            }

            QTableWidget {
                background-color: #0d1a2d;
                border: 1px solid #183252;
                border-radius: 12px;
                padding: 5px;
                selection-background-color: #2563eb;
                selection-color: white;
            }

            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #223046;
            }

            QHeaderView::section {
                background-color: #10233b;
                color: white;
                padding: 12px;
                border: none;
                font-weight: bold;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title = QLabel("Rapports Réseau")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: white;
        """)

        subtitle = QLabel(
            "Gestion et génération des rapports réseau globaux"
        )

        subtitle.setStyleSheet("""
            color: #94a3b8;
            font-size: 14px;
            padding-bottom: 15px;
        """)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.generate_btn = QPushButton("Générer Rapport Global")
        self.generate_btn.setMinimumHeight(45)
        self.generate_btn.clicked.connect(self.generate_report)

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setMinimumHeight(45)
        self.refresh_btn.clicked.connect(self.load_reports)

        self.export_pdf_btn = QPushButton("Exporter PDF")
        self.export_pdf_btn.setMinimumHeight(45)
        self.export_pdf_btn.clicked.connect(self.export_selected_pdf)

        button_layout.addWidget(self.generate_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.export_pdf_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Nom du rapport",
            "Utilisateur",
            "Date"
        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        self.table.verticalHeader().setVisible(False)

        self.table.setShowGrid(False)

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.table.setMinimumHeight(520)

        main_layout.addWidget(self.table)

    def extract_data(self, response):

        if isinstance(response, dict):

            if "data" in response and isinstance(response["data"], dict):
                return response["data"]

            return response

        return {}

    def get_error_message(self, data):

        if not isinstance(data, dict):
            return str(data)

        if data.get("detail"):
            return str(data.get("detail"))

        if data.get("message"):
            return str(data.get("message"))

        if data.get("error"):
            return str(data.get("error"))

        return str(data)

    def open_pdf_file(self, pdf_path):

        if not pdf_path:
            return

        pdf_path = os.path.abspath(pdf_path)

        if not os.path.exists(pdf_path):

            QMessageBox.warning(
                self,
                "PDF introuvable",
                f"Le fichier PDF est introuvable :\n{pdf_path}"
            )

            return

        try:

            if sys.platform.startswith("win"):

                os.startfile(pdf_path)

            elif hasattr(os, "uname") and "microsoft" in os.uname().release.lower():

                windows_path = pdf_path.replace(
                    "/mnt/c/",
                    "C:/"
                ).replace("/", "\\")

                subprocess.Popen([
                    "explorer.exe",
                    windows_path
                ])

            elif sys.platform.startswith("linux"):

                subprocess.Popen([
                    "xdg-open",
                    pdf_path
                ])

            elif sys.platform.startswith("darwin"):

                subprocess.Popen([
                    "open",
                    pdf_path
                ])

        except Exception as e:

            QMessageBox.warning(
                self,
                "Ouverture PDF",
                f"PDF généré, mais ouverture automatique impossible.\n{str(e)}"
            )

    def generate_report(self):

        try:

            response = self.api_client.generate_global_report()

            data = self.extract_data(response)

            if data.get("status") == "success":

                QMessageBox.information(
                    self,
                    "Succès",
                    "Le rapport global a été généré avec succès."
                )

                self.load_reports()

            else:

                QMessageBox.warning(
                    self,
                    "Erreur",
                    self.get_error_message(data)
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erreur",
                str(e)
            )

    def load_reports(self):

        try:

            response = self.api_client.get_reports()

            data = self.extract_data(response)

            reports = data.get("reports", [])

            self.table.setRowCount(len(reports))

            for row, report in enumerate(reports):

                item_id = QTableWidgetItem(
                    str(report.get("id", ""))
                )

                item_name = QTableWidgetItem(
                    report.get("report_name", "")
                )

                item_user = QTableWidgetItem(
                    str(report.get("user_id", ""))
                )

                item_date = QTableWidgetItem(
                    report.get("created_at", "")
                )

                item_id.setTextAlignment(Qt.AlignCenter)
                item_user.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(row, 0, item_id)
                self.table.setItem(row, 1, item_name)
                self.table.setItem(row, 2, item_user)
                self.table.setItem(row, 3, item_date)

            self.table.resizeRowsToContents()

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erreur chargement rapports",
                str(e)
            )

    def export_selected_pdf(self):

        selected_row = self.table.currentRow()

        if selected_row < 0:

            QMessageBox.warning(
                self,
                "Aucun rapport",
                "Veuillez sélectionner un rapport."
            )

            return

        try:

            report_id_item = self.table.item(selected_row, 0)

            if not report_id_item:
                return

            report_id = int(report_id_item.text())

            response = self.api_client.export_report_pdf(report_id)

            data = self.extract_data(response)

            if data.get("status") == "success":

                pdf_path = data.get("pdf_path", "")

                QMessageBox.information(
                    self,
                    "Succès",
                    "Le PDF a été généré avec succès."
                )

                self.open_pdf_file(pdf_path)

            else:

                QMessageBox.warning(
                    self,
                    "Erreur export PDF",
                    self.get_error_message(data)
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Erreur",
                str(e)
            )