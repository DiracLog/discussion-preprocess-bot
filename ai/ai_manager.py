import logging
import os

from audio.gpu_setup import setup_windows_cuda_paths
from audio.transcriber import Transcriber
from ai.engine.analyst import StructureAnalyst
from storage.memory import StorageMind


class AIContainer:
    """
    Simple dependency container holding all AI services.
    """

    def __init__(self, transcriber, analyst, memory):
        self.transcriber = transcriber
        self.analyst = analyst
        self.memory = memory


def initialize_ai() -> AIContainer:
    """
    Initializes all AI-related services once at startup.
    """

    logging.info("⏳ Initializing AI services...")


    ai_mode = os.getenv("AI_MODE", "local")
    # Important: configure CUDA paths first


    if ai_mode == "api":
        from ai.api.transcriber_api import APITranscriber
        from ai.api.analyst_api import APIAnalyst

        transcriber = APITranscriber()
        analyst = APIAnalyst()

    else:
        setup_windows_cuda_paths()
        from audio.transcriber import Transcriber
        from ai.engine.analyst import StructureAnalyst

        transcriber = Transcriber()
        analyst = StructureAnalyst()

    memory = StorageMind()

    logging.info("✅ AI services ready.")

    return AIContainer(
        transcriber=transcriber,
        analyst=analyst,
        memory=memory
    )
