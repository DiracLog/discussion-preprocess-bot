import os
import requests
import logging

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class APITranscriber:

    def __init__(self):
        self.endpoint = os.getenv("TRANSCRIBE_API_URL")
        self.token = os.getenv("TRANSCRIBE_API_TOKEN")
        self.model = os.getenv("TRANSCRIBE_MODEL", "whisper-1")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _request(self, file_path):
        with open(file_path, "rb") as f:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.token}"
                },
                files={
                    "file": (os.path.basename(file_path), f, "audio/wav")
                },
                data={
                    "model": self.model,
                    "language": "uk"
                },
                timeout=120
            )

        if not response.ok:
            logger.error("Transcribe failed: %s", response.text)
        response.raise_for_status()
        return response.json()

    def transcribe_file(self, file_path: str) -> str:
        data = self._request(file_path)
        return data.get("text", "")
