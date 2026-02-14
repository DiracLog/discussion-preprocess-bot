import logging
import os
from dataclasses import dataclass
from typing import Optional, Iterable

import torch
from faster_whisper import WhisperModel

from .gpu_setup import setup_windows_cuda_paths

logger = logging.getLogger(__name__)


# ---------------------- CONFIG ----------------------

@dataclass
class TranscriberConfig:
    model_size: str = "large-v3"
    device: Optional[str] = None
    compute_type: str = "int8"
    language: Optional[str] = "uk"
    beam_size: int = 5


# ---------------------- TRANSCRIBER ----------------------

class Transcriber:

    def __init__(self, config: Optional[TranscriberConfig] = None):
        self.config = config or TranscriberConfig()

        setup_windows_cuda_paths()

        if self.config.device is None:
            self.config.device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(
            f"Loading Whisper model '{self.config.model_size}' "
            f"on {self.config.device}..."
        )

        self.model = WhisperModel(
            self.config.model_size,
            device=self.config.device,
            compute_type=self.config.compute_type
        )

        logger.info("Whisper model loaded successfully.")

    # ---------------------- PUBLIC API ----------------------

    def transcribe_file(self, file_path: str) -> str:
        """
        Transcribes an audio file and returns full text.
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return ""

        try:
            segments = self._transcribe(file_path)
            return " ".join(segment.text.strip() for segment in segments)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def transcribe_stream(self, audio_source) -> str:
        """
        Transcribe from file-like object or numpy array.
        """
        try:
            segments = self._transcribe(audio_source)
            return " ".join(segment.text.strip() for segment in segments)
        except Exception as e:
            logger.error(f"Stream transcription failed: {e}")
            return ""

    # ---------------------- INTERNAL ----------------------

    def _transcribe(self, source) -> Iterable:
        segments, info = self.model.transcribe(
            source,
            language=self.config.language,
            beam_size=self.config.beam_size
        )

        logger.info(f"Audio duration: {info.duration:.2f}s")

        return list(segments)
