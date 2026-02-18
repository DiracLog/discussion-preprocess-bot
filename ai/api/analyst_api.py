import os
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from ai.engine.parser import JSONParser

logger = logging.getLogger(__name__)


class APIAnalyst:

    def __init__(self):
        self.endpoint = os.getenv("ANALYST_API_URL")
        self.token = os.getenv("ANALYST_API_TOKEN")
        self.model = os.getenv("ANALYST_MODEL", "mixtral-8x7b-32768")
        self.parser = JSONParser()

    # retry automatically on failure
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _request(self, payload):
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )
        if not response.ok:
            logger.error("Analyst API error: %s", response.text)
        response.raise_for_status()
        return response.json()

    def smart_summarize(self, text: str) -> dict:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You are an analytical meeting summarizer. Output ONLY valid JSON."},
                {"role": "user", "content": text}
            ]
        }

        data = self._request(payload)

        choices = data.get("choices", [])
        if not choices:
            logger.error("Empty analyst response: %s", data)
            return {}

        raw = choices[0].get("message", {}).get("content", "")
        return self.parser.parse(raw)

