import logging
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from .config import AnalystConfig


class ModelLoader:
    def __init__(self, config: AnalystConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def load(self) -> Llama:
        try:
            self.logger.info(f"Downloading/Loading model: {self.config.filename}")

            if self.config.local_model_path:
                model_path = self.config.local_model_path
            else:
                model_path = hf_hub_download(
                    repo_id=self.config.repo_id,
                    filename=self.config.filename
                )

            self.logger.info(f"Initializing Llama from: {model_path}")

            return Llama(
                model_path=model_path,
                n_gpu_layers=self.config.n_gpu_layers,
                n_ctx=self.config.n_ctx,
                verbose=False
            )

        except Exception as e:
            self.logger.error(f"Model loading failed: {e}")
            raise
