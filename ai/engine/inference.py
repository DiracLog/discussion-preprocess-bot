import time
import logging
from llama_cpp import Llama
from .config import AnalystConfig


class InferenceEngine:
    def __init__(self, llm: Llama, config: AnalystConfig):
        self.llm = llm
        self.config = config
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, max_tokens: int) -> str:
        start_time = time.time()

        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=self.config.temperature,
            stop=["</s>"],
            echo=False
        )

        duration = time.time() - start_time
        self.logger.info(f"⚡ Inference complete in {duration:.2f}s")

        try:
            return output["choices"][0]["text"].strip()
        except Exception:
            self.logger.error("Invalid LLM output format")
            return ""
