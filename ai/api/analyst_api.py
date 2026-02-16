import requests
import os


class APIAnalyst:

    def __init__(self):
        self.endpoint = os.getenv("ANALYST_API_URL")
        self.token = os.getenv("ANALYST_API_TOKEN")

    def smart_summarize(self, text: str) -> dict:
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"text": text}
        )

        if response.status_code != 200:
            return {"reviews": []}

        return response.json()