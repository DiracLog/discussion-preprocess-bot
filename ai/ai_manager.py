import logging

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

    # Important: configure CUDA paths first
    setup_windows_cuda_paths()

    transcriber = Transcriber()
    analyst = StructureAnalyst()
    memory = StorageMind()

    logging.info("✅ AI services ready.")

    return AIContainer(
        transcriber=transcriber,
        analyst=analyst,
        memory=memory
    )
