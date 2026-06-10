import requests

BASE_URL = "http://127.0.0.1:8000"


class ApiClient:
    def __init__(self):
        self.token = None
        self.current_user = None

    def extract_error_message(self, response):
        try:
            data = response.json()

            if isinstance(data, dict):
                if "detail" in data:
                    return data["detail"]
                if "message" in data:
                    return data["message"]
                if "error" in data:
                    return data["error"]

            return str(data)

        except Exception:
            return response.text

    # =========================
    # AUTH
    # =========================
    def login(self, username, password):
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                data={
                    "username": username,
                    "password": password
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")

                return {
                    "success": True,
                    "token": self.token,
                    "data": data
                }

            return {
                "success": False,
                "error": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_headers(self):
        headers = {
            "Content-Type": "application/json"
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def get_me(self):
        try:
            response = requests.get(
                f"{BASE_URL}/auth/me",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                self.current_user = response.json()

                return {
                    "success": True,
                    "data": self.current_user
                }

            return {
                "success": False,
                "error": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # =========================
    # GENERIC REQUESTS
    # =========================
    def get(self, endpoint):
        try:
            response = requests.get(
                f"{BASE_URL}{endpoint}",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }

            return {
                "success": False,
                "error": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def post(self, endpoint, payload=None, timeout=30):
        try:
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=payload,
                headers=self.get_headers(),
                timeout=timeout
            )

            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "data": response.json()
                }

            return {
                "success": False,
                "error": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def put(self, endpoint, payload=None):
        try:
            response = requests.put(
                f"{BASE_URL}{endpoint}",
                json=payload,
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }

            return {
                "success": False,
                "error": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def delete(self, endpoint):
        try:
            response = requests.delete(
                f"{BASE_URL}{endpoint}",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }

            return {
                "success": False,
                "error": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # =========================
    # USERS
    # =========================
    def get_users(self):
        return self.get("/admin/users")

    def create_user(self, payload):
        return self.post("/admin/create-user", payload)

    def update_user_role(self, user_id, payload):
        return self.put(f"/admin/update-role/{user_id}", payload)

    def delete_user(self, user_id):
        return self.delete(f"/admin/delete-user/{user_id}")

    # =========================
    # NETWORK DISCOVERY
    # =========================
    def discover_network(self, payload):
        return self.post("/network/site", payload, timeout=600)

    def get_latest_architecture_report(self):
        return self.get("/reports/last")

    def get_architecture_report(self, report_id):
        return self.get(f"/reports/{report_id}")

    # =========================
    # VLAN / VLSM
    # =========================
    def generate_vlsm(self, payload):
        return self.post("/network/generate-vlsm", payload)

    def generate_vlans(self, payload):
        return self.post("/generate-vlan", payload)

    def render_network(self, payload):
        return self.post("/render-network", payload)

    def deploy_network_configs(self, devices):
        return self.post(
            "/deploy-network",
            {
                "devices": devices
            },
            timeout=60
        )

    # =========================
    # ACL
    # =========================
    def process_acl(self, report, policies):
        return self.post(
            "/generate-acl",
            {
                "report": report,
                "policies": policies
            }
        )

    def generate_acl_commands(self, report, policies):
        return self.post(
            "/render-acl",
            {
                "report": report,
                "policies": policies
            }
        )

    def deploy_aclconfig(self, devices):
        return self.post(
            "/deploy-acl-configs",
            {
                "devices": devices
            },
            timeout=60
        )

    # =========================
    # NOTIFICATIONS
    # =========================
    def get_notifications(self):
        return self.get("/notifications")

    def get_user_notifications(self):
        return self.get_notifications()

    def mark_notification_read(self, notification_id):
        return self.put(f"/notifications/{notification_id}/read")

    def mark_notification_as_read(self, notification_id):
        return self.mark_notification_read(notification_id)

    # =========================
    # EMAIL SETTINGS
    # =========================
    def save_email_settings(self, payload):
        return self.post("/email-settings/save", payload)

    def get_email_settings(self):
        return self.get("/email-settings")

    # =========================
    # DASHBOARD
    # =========================
    def get_dashboard_summary(self):
        return self.get("/dashboard/summary")

    def get_ai_score_history(self, user_id):
        return self.get(f"/ai/score-history/{user_id}")

    # =========================
    # SAVED ARCHITECTURES
    # =========================
    def get_saved_sites(self):
        try:
            response = requests.get(
                f"{BASE_URL}/architecture/sites",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return response.json()

            return {
                "success": False,
                "message": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def get_architecture_by_id(self, report_id):
        try:
            response = requests.get(
                f"{BASE_URL}/architecture/{report_id}",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return response.json()

            return {
                "success": False,
                "message": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def delete_architecture(self, report_id):
        try:
            response = requests.delete(
                f"{BASE_URL}/architecture/{report_id}",
                headers=self.get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return response.json()

            return {
                "success": False,
                "message": self.extract_error_message(response),
                "status_code": response.status_code
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def get_audit_logs(self, limit=100):
        return self.get(f"/audit/logs?limit={limit}")

    def get_security_analytics(self):
        return self.get("/security/analytics")

    def has_admin(self):
        return self.get("/auth/has-admin")

    def setup_admin(self, payload):
        return self.post("/auth/setup_admin", payload)

    def get_reports(self):
        return self.get("/reports/list")

    def generate_global_report(self):
        return self.post("/reports/generate-global")

    def export_report_pdf(self, report_id):
        return self.post(f"/reports/export-pdf/{report_id}")

    def open_report_pdf(self, pdf_path):
        import os
        os.startfile(pdf_path)