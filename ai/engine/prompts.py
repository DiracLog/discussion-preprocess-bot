class PromptBuilder:

    @staticmethod
    def build_chunk_prompt(chunk: str) -> str:
        return f"""[INST]
                АНАЛІЗ СЕГМЕНТУ (Raw Data Extraction).
                
                1. Знайди всі згадки медіа (фільми, ігри, книги).
                2. Випиши цифрові оцінки.
                3. Випиши аргументи та хто це сказав.
                
                ФОРМАТ:
                - Спікер: [Ім'я] | Твір: [Назва] | Оцінка: [Число/Фраза] | Думка: [Аргументи]
                
                Якщо нічого немає — напиши "ПУСТО".
                
                ТЕКСТ:
                {chunk}
                [/INST]"""

    @staticmethod
    def build_main_prompt(text: str, is_notes: bool) -> str:
        input_desc = (
            "Це попередньо зібрані нотатки."
            if is_notes
            else "Це сира стенограма."
        )

        return f"""[INST]
                    Ти - аналітик книжкового клубу.
                    {input_desc}
                    
                    Формат виводу: ТІЛЬКИ валідний JSON:
                    
                    {{
                      "reviews": [
                        {{
                          "title": "Назва твору",
                          "type": "book/movie/game/series",
                          "sentiment": "positive/negative/mixed",
                          "arguments": [],
                          "mark": 8.5,
                          "is_inferred_score": true,
                          "speaker": "Ім'я"
                        }}
                      ]
                    }}
                    
                    ТЕКСТ:
                    {text}
                    [/INST]"""
