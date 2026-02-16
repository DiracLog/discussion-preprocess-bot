import requests
import os


class APITranscriber:

    def __init__(self):
        self.endpoint = os.getenv("TRANSCRIBE_API_URL")
        self.token = os.getenv("TRANSCRIBE_API_TOKEN")

    def transcribe_file(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            response = requests.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.token}"},
                files={"file": f},
                timeout=120
            )

        response.raise_for_status()

        return response.json().get("text", "")