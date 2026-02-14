import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from huggingface_hub import hf_hub_download
from llama_cpp import Llama


# ---------------------- CONFIG ----------------------

@dataclass
class AnalystConfig:
    repo_id: str = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
    filename: str = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    context_limit: int = 5000
    chunk_size: int = 15000
    overlap: int = 1000
    max_tokens_standard: int = 4096
    max_tokens_chunk: int = 1024
    temperature: float = 0.1
    n_ctx: int = 8192
    n_gpu_layers: int = -1


# ---------------------- MAIN CLASS ----------------------

class StructureAnalyst:
    def __init__(self, config: AnalystConfig = AnalystConfig()):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.info(f"Downloading/Loading model: {config.filename}")
        model_path = hf_hub_download(
            repo_id=config.repo_id,
            filename=config.filename
        )

        self.logger.info(f"Initializing Llama from: {model_path}")
        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=config.n_gpu_layers,
            n_ctx=config.n_ctx,
            verbose=False  # Set to True if C++ debug logs are needed
        )
        self.logger.info("✅ Analyst Model loaded successfully.")

    # ---------------------- PUBLIC API ----------------------

    def smart_summarize(self, text: str) -> Dict[str, Any]:
        """
        Main entry point. Automatically decides between One-Shot or Map-Reduce.
        """
        if self._is_short(text):
            self.logger.info("🟢 Text fits context. Running standard analysis...")
            return self._extract_structure(text)

        self.logger.info(f"🔴 Long text detected. Engaging Map-Reduce...")
        return self._map_reduce_analysis(text)

    # Legacy alias for backward compatibility if needed
    def extract_structure(self, text: str) -> Dict[str, Any]:
        return self.smart_summarize(text)

    # ---------------------- INTERNAL LOGIC ----------------------

    def _is_short(self, text: str) -> bool:
        estimated_tokens = len(text) // 4
        return estimated_tokens < self.config.context_limit

    def _map_reduce_analysis(self, text: str) -> Dict[str, Any]:
        chunks = self._split_text(text)
        summaries = []

        for i, chunk in enumerate(chunks):
            self.logger.info(f"🧠 Processing Chunk {i + 1}/{len(chunks)}...")
            prompt = self._build_chunk_prompt(chunk)
            response = self._generate(prompt, self.config.max_tokens_chunk)
            summaries.append(response)

        self.logger.info("🔗 Combining chunk summaries...")
        combined_text = "\n".join(summaries)

        # Final Pass: Extract clean JSON from the intermediate notes
        return self._extract_structure(combined_text, is_notes=True)

    def _split_text(self, text: str) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.config.chunk_size, text_len)
            chunks.append(text[start:end])
            if end == text_len:
                break
            start += self.config.chunk_size - self.config.overlap
        return chunks

    def _extract_structure(self, text: str, is_notes: bool = False) -> Dict[str, Any]:
        self.logger.info("🧠 Generating final structured JSON...")
        prompt = self._build_main_prompt(text, is_notes)
        raw_output = self._generate(prompt, self.config.max_tokens_standard)

        clean_json = self._clean_json_string(raw_output)

        try:
            return json.loads(clean_json)
        except json.JSONDecodeError:
            self.logger.error(f"❌ Failed to parse JSON. Raw output:\n{raw_output}")
            # Return empty structure to prevent crash
            return {"reviews": []}

    # ---------------------- PROMPTS ----------------------

    def _build_chunk_prompt(self, chunk: str) -> str:
        return f"""[INST]
АНАЛІЗ СЕГМЕНТУ (Raw Data Extraction).
Твоє завдання — витягнути конкретні факти.

1. Знайди всі згадки медіа (фільми, ігри, книги). Збережи оригінальну назву.
2. Випиши цифрові оцінки (наприклад "8 з 10") дослівно.
3. Випиши конкретні аргументи (чому сподобалось/не сподобалось) і ХТО це сказав (Спікер).

ФОРМАТ ВІДПОВІДІ (Список):
- Спікер: [Ім'я] | Твір: [Назва] | Оцінка: [Число/Фраза] | Думка: [Аргументи]
...

Якщо у цьому шматку немає обговорення творів, напиши "ПУСТО".

ТЕКСТ СЕГМЕНТУ:
{chunk}
[/INST]"""

    def _build_main_prompt(self, text: str, is_notes: bool) -> str:
        input_desc = "Це попередньо зібрані нотатки (факти) з довгої розмови." if is_notes else "Це сира стенограма (transcript)."

        return f"""[INST]
Ти - аналітик книжкового клубу.
{input_desc}

Твоє завдання:
1. Знайти ВСІ обговорені твори.
2. Для кожного твору і КОЖНОГО спікера створити ОКРЕМИЙ запис. 
3. НЕ змішувати думки різних людей. Якщо Андрій і Олексій говорили про "Дюну", це має бути ДВА різних об'єкти в списку.

Формат виводу: ТІЛЬКИ валідний JSON об'єкт (без markdown блоків ```json):
{{
  "reviews": [
    {{
      "title": "Назва твору",
      "type": "book/movie/game/series",
      "sentiment": "positive/negative/mixed",
      "arguments": ["Аргумент 1", ...],
      "mark": 8.5, 
      "is_inferred_score": true,
      "speaker": "Ім'я спікера (ОБОВ'ЯЗКОВО)" 
    }}
  ]
}}

ТЕКСТ ДЛЯ АНАЛІЗУ:
{text}
[/INST]"""

    # ---------------------- LLM CORE ----------------------

    def _generate(self, prompt: str, max_tokens: int) -> str:
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

        return output['choices'][0]['text'].strip()

    # ---------------------- UTILS ----------------------

    @staticmethod
    def _clean_json_string(text: str) -> str:
        # 1. Regex for markdown code blocks
        json_block = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
        if json_block:
            return json_block.group(1).strip()

        # 2. Fallback: Find outer braces
        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace != -1 and last_brace != -1:
            return text[first_brace:last_brace + 1]

        return text


# ---------------------- ENTRY POINT ----------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Simple test
    analyst = StructureAnalyst()
    dummy_text = "[10:00] Andrii: Дюна - це шедевр, 10/10. Alex: Не згоден, нудно, 5/10."

    result = analyst.smart_summarize(dummy_text)
    print(json.dumps(result, indent=2, ensure_ascii=False))