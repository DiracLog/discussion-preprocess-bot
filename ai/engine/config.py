from dataclasses import dataclass
from typing import Optional

@dataclass
class AnalystConfig:
    repo_id: str = "TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
    filename: str = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"

    local_model_path: Optional[str] = None

    context_limit: int = 5000
    chunk_size: int = 15000
    overlap: int = 1000

    max_tokens_standard: int = 4096
    max_tokens_chunk: int = 1024
    temperature: float = 0.1

    n_ctx: int = 8192
    n_gpu_layers: int = -1
