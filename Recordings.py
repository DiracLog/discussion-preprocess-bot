import os
import torch
from faster_whisper import WhisperModel

def setup_dlls():
    if os.name == 'nt':
        print("--- 🔗 LINKING GPU LIBRARIES (AGGRESSIVE MODE) ---")
        paths_to_add = []

        try:
            # 1. PyTorch Internal Libs
            import torch
            torch_lib = os.path.join(os.path.dirname(torch.__file__), 'lib')
            paths_to_add.append(torch_lib)

            # 2. NVIDIA Package Libs (The critical fix)
            site_packages = os.path.dirname(os.path.dirname(torch.__file__))
            nvidia_path = os.path.join(site_packages, 'nvidia')

            if os.path.exists(nvidia_path):
                for root, dirs, files in os.walk(nvidia_path):
                    if 'bin' in dirs:
                        paths_to_add.append(os.path.join(root, 'bin'))
                    if 'lib' in dirs:
                        paths_to_add.append(os.path.join(root, 'lib'))

        except ImportError:
            pass

        # 3. Add to BOTH 'PATH' and 'add_dll_directory'
        count = 0
        for path in paths_to_add:
            if os.path.exists(path):
                # METHOD A: The Modern Way (Python 3.8+)
                try:
                    os.add_dll_directory(path)
                    count += 1
                except Exception as e:
                    print(f"  ⚠️ add_dll_directory failed for {path}: {e}")

                # METHOD B: The Old School Fail-Safe (Updates process PATH)
                if path not in os.environ['PATH']:
                    os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                    print(f"  👉 Force-added to PATH: {path}")

        print(f"  ✅ Registered {count} DLL directories (and updated PATH).")

setup_dlls()



class Transcriber:
    def __init__(self, model_size="large-v3", device=None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"⏳ Loading Whisper ({model_size}) on {device}...")
        compute_type = "int8"

        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print("✅ Whisper Loaded.")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise e

    def transcribe_file(self, file_path):
        if not os.path.exists(file_path): return ""

        print(f"   🎧 Processing audio file...")

        full_text = []
        try:
            segments, info = self.model.transcribe(file_path, language="uk", beam_size=5)

            # UPDATED: Print progress in real-time
            print(f"   Detected Duration: {info.duration:.2f}s. Transcribing...")

            for segment in segments:
                # Show the text as it is generated
                print(f"      [{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
                full_text.append(segment.text)

        except RuntimeError as e:
            print(f"❌ Whisper Error: {e}")
            return ""

        return " ".join(full_text)


if __name__ == "__main__":
    t = Transcriber()
    print("Transcriber ready.")