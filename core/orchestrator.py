import asyncio
import shutil
import os
from datetime import datetime
import logging
from typing import List, Tuple
import discord

logger = logging.getLogger(__name__)

class ScribeOrchestrator:

    def __init__(self, transcriber, analyst, memory, session_manager):
        self.transcriber = transcriber
        self.analyst = analyst
        self.memory = memory
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)

    # ---------------- CUT PROCESSING ----------------

    async def process_cut(
            self,
            guild: discord.Guild,
            files: List[Tuple[int, str]]
    ) -> str:
        loop = asyncio.get_running_loop()
        guild_id = guild.id

        processed_paths = []  # <-- add this

        def task():
            results = []

            for user_id, filepath in files:
                try:
                    member = guild.get_member(user_id)
                    name = member.display_name if member else f"User_{user_id}"

                    logger.info(
                        "Sending file to STT: %s (size=%d bytes)",
                        filepath,
                        os.path.getsize(filepath)
                    )

                    text = self.transcriber.transcribe_file(filepath)

                    if text.strip():
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        entry = f"[{timestamp}] {name}: {text}"
                        self.session_manager.add_entry(guild_id, entry)
                        results.append(f"**{name}:** {text}")

                    os.makedirs("processed", exist_ok=True)
                    new_path = os.path.join("processed", os.path.basename(filepath))
                    shutil.move(filepath, new_path)

                    processed_paths.append(new_path)  # <-- store

                except Exception as e:
                    self.logger.error(f"process_cut error: {e}")
                    continue

            return "\n".join(results)

        result_text = await loop.run_in_executor(None, task)

        # DEBUG: send one processed file
        if processed_paths:
            channel = guild.system_channel or guild.text_channels[0]
            await channel.send(file=discord.File(processed_paths[0]))

        return result_text

    # ---------------- SUMMARIZE ----------------

    async def summarize(self, guild_id: int, user_name: str, speakers: list[str] | None = None):
        history = self.session_manager.get_history(guild_id)

        if not history:
            return None

        loop = asyncio.get_running_loop()
        full_text = "\n".join(history)

        def analysis():
            return self.analyst.smart_summarize(full_text)

        result = await loop.run_in_executor(None, analysis)

        # ---------- COLD STORAGE ----------
        log_id = self.memory.archive_session_log(
            transcript=full_text,
            analysis=result,
            user_name=user_name
        )

        # ---------- VECTOR STORAGE ----------
        if speakers:
            def save_vectors():
                reviews = result.get("reviews", [])
                if not isinstance(reviews, list):
                    reviews = [reviews]

                for review in reviews:
                    self.memory.store_insights(
                        analysis_item=review,
                        original_transcription=full_text,
                        speaker_id=", ".join(speakers),
                        full_log_id=log_id
                    )

            await loop.run_in_executor(None, save_vectors)

        return result, log_id

    # ---------------- SEARCH ----------------

    async def search(self, query: str, filter_user: str | None = None):
        loop = asyncio.get_running_loop()

        def task():
            return self.memory.search(
                query_text=query,
                filter_user=filter_user,
                n_results=3
            )

        return await loop.run_in_executor(None, task)
