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
                files={"file": f}
            )

        if response.status_code != 200:
            return ""

        return response.json().get("text", "")