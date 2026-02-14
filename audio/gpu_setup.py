import os
import logging

logger = logging.getLogger(__name__)


def setup_windows_cuda_paths():
    """
    Adds CUDA DLL directories to PATH on Windows if needed.
    Safe to call multiple times.
    """
    if os.name != "nt":
        return

    try:
        import torch
    except ImportError:
        return

    paths_to_add = []

    torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    paths_to_add.append(torch_lib)

    site_packages = os.path.dirname(os.path.dirname(torch.__file__))
    nvidia_path = os.path.join(site_packages, "nvidia")

    if os.path.exists(nvidia_path):
        for root, dirs, _ in os.walk(nvidia_path):
            if "bin" in dirs:
                paths_to_add.append(os.path.join(root, "bin"))
            if "lib" in dirs:
                paths_to_add.append(os.path.join(root, "lib"))

    for path in set(paths_to_add):
        if os.path.exists(path):
            try:
                os.add_dll_directory(path)
            except Exception:
                pass

            if path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")

    logger.info("CUDA DLL paths configured (Windows).")
