import requests
import os
from ai.engine.prompts import PromptBuilder

class APIAnalyst:

    def __init__(self):
        self.endpoint = os.getenv("ANALYST_API_URL")
        self.token = os.getenv("ANALYST_API_TOKEN")

    def smart_summarize(self, text: str) -> dict:
        prompt = PromptBuilder.build_main_prompt(text, is_notes=False)

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": prompt
            },
            timeout=120
        )

        response.raise_for_status()

        return response.json()