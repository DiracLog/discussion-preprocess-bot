import logging
from .config import AnalystConfig
from .model_loader import ModelLoader
from .inference import InferenceEngine
from .chunking import TextChunker
from .prompts import PromptBuilder
from .parser import JSONParser


class StructureAnalyst:
    def __init__(self, config: AnalystConfig | None = None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.config = config or AnalystConfig()


        # Build components
        loader = ModelLoader(self.config)
        llm = loader.load()

        self.inference = InferenceEngine(llm, self.config)
        self.chunker = TextChunker(self.config.chunk_size, self.config.overlap)
        self.parser = JSONParser()

    # -------- Public API --------

    def smart_summarize(self, text: str) -> dict:
        if self._is_short(text):
            return self._analyze(text)

        return self._map_reduce(text)

    # -------- Internal --------

    def _is_short(self, text: str) -> bool:
        return len(text) // 4 < self.config.context_limit

    def _map_reduce(self, text: str) -> dict:
        chunks = self.chunker.split(text)
        summaries = []

        for chunk in chunks:
            prompt = PromptBuilder.build_chunk_prompt(chunk)
            result = self.inference.generate(
                prompt,
                self.config.max_tokens_chunk
            )
            summaries.append(str(result))

        combined = "\n".join(summaries)
        return self._analyze(combined, is_notes=True)

    def _analyze(self, text: str, is_notes: bool = False) -> dict:
        prompt = PromptBuilder.build_main_prompt(text, is_notes)
        raw = self.inference.generate(
            prompt,
            self.config.max_tokens_standard
        )
        return self.parser.parse(raw)
