import logging
import os


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

    transcriber_mode = os.getenv("TRANSCRIBER_MODE", "local")
    analyst_mode = os.getenv("ANALYST_MODE", "local")

    if "local" in [transcriber_mode, analyst_mode]:
        from audio.gpu_setup import setup_windows_cuda_paths
        setup_windows_cuda_paths()

    if transcriber_mode == "api":
        from ai.api.transcriber_api import APITranscriber
        transcriber = APITranscriber()
    else:
        from audio.transcriber import Transcriber
        transcriber = Transcriber()

    if analyst_mode == "api":
        from ai.api.analyst_api import APIAnalyst
        analyst = APIAnalyst()
    else:
        from ai.engine.analyst import StructureAnalyst
        analyst = StructureAnalyst()

    memory = StorageMind()

    logging.info("✅ AI services ready.")

    return AIContainer(
        transcriber=transcriber,
        analyst=analyst,
        memory=memory
    )
