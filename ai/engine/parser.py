import json
import re
import logging


class JSONParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(self, text: str) -> dict:
        clean = self._clean_json_string(text)

        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # attempt soft cleanup
            clean = clean.replace("\n", " ").strip()

            try:
                return json.loads(clean)
            except Exception:
                self.logger.error(f"Failed to parse JSON:\n{text}")
                return {"topics": []}

    @staticmethod
    def _clean_json_string(text: str) -> str:
        json_block = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
        if json_block:
            return json_block.group(1).strip()

        first = text.find("{")
        last = text.rfind("}")

        if first != -1 and last != -1:
            return text[first:last + 1]

        return text
