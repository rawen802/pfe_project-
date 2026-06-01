from services.api_client import ApiClient


class DashboardService:
    def __init__(self, api_client: ApiClient):
        self.api = api_client

    def get_ai_score(self, user_id: int):
        try:
            data = self.api.get(f"/ai/score-history/{user_id}")

            if isinstance(data, list) and data:
                last = data[-1]
                return last.get("score", 0)

            if isinstance(data, dict):
                if "scores" in data and data["scores"]:
                    return data["scores"][-1].get("score", 0)
                if "history" in data and data["history"]:
                    return data["history"][-1].get("score", 0)
                return data.get("score", 0)

        except Exception:
            return 0

        return 0

    def get_users_count(self):
        try:
            data = self.api.get("/admin/users")

            if isinstance(data, list):
                return len(data)

            if isinstance(data, dict):
                if "users" in data and isinstance(data["users"], list):
                    return len(data["users"])
                if "data" in data and isinstance(data["data"], list):
                    return len(data["data"])

        except Exception:
            return 0

        return 0

    def get_dashboard_data(self, user_id: int, role: str):
        ai_score = self.get_ai_score(user_id)

        users_count = 0
        if role == "admin":
            users_count = self.get_users_count()

        return {
            "ai_score": ai_score,
            "users_count": users_count,
            "alerts_count": 0,
            "devices_count": 0,
        }