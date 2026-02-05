import json
import time
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
import re
import textwrap


class StructureAnalyst:
    def __init__(self, repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
                 filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf"):
        print(f"⏳ Loading Analyst ({filename})...")
        model_path = hf_hub_download(repo_id=repo_id, filename=filename)
        self.context_limit = 5000

        self.llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1,
            n_ctx=8192,
            verbose=True  # Keeps C++ logs enabled just in case
        )
        print("✅ Analyst Loaded.")

    @staticmethod
    def extract_json(txt):
        # 1. Try to find a JSON block inside Markdown tags
        pattern = r"```json(.*?)```"
        match = re.search(pattern, txt, re.DOTALL)

        if match:
            return match.group(1).strip()

        # 2. Fallback: Look for the first outer curly braces { ... }
        # This saves you if the model forgets the Markdown tags entirely
        pattern_fallback = r"\{.*\}"
        match_fallback = re.search(pattern_fallback, txt, re.DOTALL)

        if match_fallback:
            return match_fallback.group(0).strip()

        return txt  # Return original if nothing found (will likely error in json.loads)

    def smart_summarize(self, full_text):
        """
        Decides whether to do a One-Shot or Map-Reduce summary
        based on length.
        """
        # 1. Estimate Token Count (Roughly 4 chars per token)
        estimated_tokens = len(full_text) / 4

        if estimated_tokens < self.context_limit:
            print("🟢 Short text. Running standard analysis...")
            return self.extract_structure(full_text)
        else:
            print(f"🔴 Long text ({int(estimated_tokens)} tokens). Engaging Map-Reduce...")
            return self.map_reduce_analysis(full_text)

    def map_reduce_analysis(self, text):
        # STEP 1: CHUNK IT
        # Split into chunks of ~15,000 characters (approx 4k tokens)
        chunks = []
        chunk_size = 15000
        overlap = 1000

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text): break
            start += chunk_size - overlap


        intermediate_summaries = []

        # STEP 2: MAP (Process each chunk)
        for i, chunk in enumerate(chunks):
            print(f"   🧠 Processing Chunk {i + 1}/{len(chunks)}...")
            prompt = f"""[INST]
                        АНАЛІЗ СЕГМЕНТУ (Raw Data Extraction).
                        Твоє завдання — витягнути конкретні факти.

                        1. Знайди всі згадки медіа (фільми, ігри, книги). Збережи оригінальну назву.
                        2. Випиши цифрові оцінки (наприклад "8 з 10") дослівно.
                        3. Випиши конкретні аргументи (чому сподобалось/не сподобалось).

                        ФОРМАТ ВІДПОВІДІ (Список):
                        - Твір: [Назва] | Оцінка: [Число/Фраза] | Аргументи: [Теза 1, Теза 2]
                        ...

                        Якщо у цьому шматку немає обговорення творів, напиши "ПУСТО".

                        ТЕКСТ СЕГМЕНТУ:
                        {chunk}
                        [/INST]"""
            # Call your LLM here (assuming self.llm is your model function)
            # Виклик моделі
            response = self.llm(
                prompt,
                max_tokens=1024,
                temperature=0.1,
                stop=["</s>"],
                top_p=0.95,
                echo=False  # dont repeat prompt
            )
            text_result = response['choices'][0]['text']
            intermediate_summaries.append(text_result)

        # STEP 3: REDUCE (Combine)
        print("   🔗 Combining summaries...")
        combined_text = "\n".join(intermediate_summaries)

        # Final Pass: Extract the clean JSON structure from the combined notes
        final_structure = self.extract_structure(combined_text, is_notes=True)

        return final_structure


    def extract_structure(self, transcription, is_notes=False):
        input_description = "Вхідний текст - це «сира» стенограма з Whisper (ASR)."
        if is_notes:
            input_description = "Вхідний текст - це попередньо зібрані нотатки (факти) з довгої розмови."

        system_prompt = f"""Ти - інтелектуальний редактор та аналітик розмов.
                {input_description}

                Твоє завдання:
                1. Сформувати фінальний JSON з усіма обговореними творами.
                2. Якщо це нотатки, об'єднай дублікати (якщо один твір згадується у кількох шматках).
                3. ВИПРАВИТИ назви та нормалізувати оцінки.

                Формат виводу: ТІЛЬКИ валідний JSON об'єкт (без markdown блоків ```json):
                {{
                  "reviews": [
                    {{
                      "title": "Назва твору",
                      "type": "book/movie/game/series",
                      "sentiment": "positive/negative/mixed",
                      "arguments": ["Аргумент 1", ...],
                      "mark": 8.5, 
                      "is_inferred_score": true
                    }}
                  ]
                }}
                """

        user_prompt = f"ДАНІ ДЛЯ АНАЛІЗУ:\n{transcription}"
        full_prompt = f"[INST] {system_prompt}\n\n{user_prompt} [/INST]"

        start_time = time.time()

        output = self.llm(
            full_prompt,
            max_tokens=4096,
            temperature=0.1,
            stop=["</s>"],
            echo=False
        )

        end_time = time.time()
        print(f"   ⚡ LLM Inference complete in {end_time - start_time:.2f} seconds.")

        raw_text = output['choices'][0]['text'].strip()

        clean_json_text = self.extract_json(raw_text)

        try:
            data = json.loads(clean_json_text)
            return data
        except json.JSONDecodeError:
            print(f"❌ Model failed to generate valid JSON. Raw text:\n{raw_text}")
            return None


if __name__ == "__main__":
    a = StructureAnalyst()
    print("Analyst ready.")