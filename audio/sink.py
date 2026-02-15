import os
import time
import wave
import collections
import discord
import discord.opus
from discord.ext import voice_recv


class ScribeSink(voice_recv.AudioSink):

    def __init__(self, temp_dir="temp_pcm", recordings_dir="recordings", flush_threshold=500):
        super().__init__()

        self.temp_dir = temp_dir
        self.recordings_dir = recordings_dir

        self.user_buffers = collections.defaultdict(list)
        self.packet_counters = collections.defaultdict(int)
        self.decoders = {}
        self.flush_threshold = flush_threshold

        os.makedirs(self.temp_dir, exist_ok=True)

    def wants_opus(self):
        return True

    def write(self, user, data):
        if user is None:
            return

        uid = user.id

        if uid not in self.decoders:
            self.decoders[uid] = discord.opus.Decoder()

        try:
            packet_bytes = getattr(data.packet, "decrypted_data", data.packet.payload)
            pcm = self.decoders[uid].decode(packet_bytes, fec=True)

            self.user_buffers[uid].append(pcm)
            self.packet_counters[uid] += 1

            if self.packet_counters[uid] >= self.flush_threshold:
                self.flush_to_disk(uid)

        except Exception as e:
            print(f"ScribeSink decode error: {e}")

    def flush_to_disk(self, uid):
        if not self.user_buffers[uid]:
            return

        filename = os.path.join(self.temp_dir, f"stream_{uid}.pcm")

        with open(filename, "ab") as f:
            f.write(b"".join(self.user_buffers[uid]))

        self.user_buffers[uid] = []
        self.packet_counters[uid] = 0

    def cleanup(self):
        for uid in list(self.user_buffers.keys()):
            self.flush_to_disk(uid)

    def save_and_clear_buffers(self):
        self.cleanup()
        saved_files = []
        ts = int(time.time())

        os.makedirs(self.recordings_dir, exist_ok=True)

        for filename in os.listdir(self.temp_dir):
            if not filename.endswith(".pcm"):
                continue

            uid = int(filename.split("_")[1].split(".")[0])
            pcm_path = os.path.join(self.temp_dir, filename)
            wav_path = os.path.join(self.recordings_dir, f"session_{uid}_{ts}.wav")

            with open(pcm_path, "rb") as f:
                data = f.read()

            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(data)

            os.remove(pcm_path)
            saved_files.append((uid, wav_path))

        return saved_files