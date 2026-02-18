import asyncio
import shutil
import os
from datetime import datetime
import logging
from typing import List, Tuple
import discord
from collections import defaultdict
import wave
from uuid import uuid4

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

        user_names = {}
        for user_id, _ in files:
            if user_id not in user_names:
                member = guild.get_member(user_id)
                user_names[user_id] = (
                    member.display_name if member else f"User_{user_id}"
                )

        def task():
            transcriptions = []
            entries = []
            user_files = defaultdict(list)

            # Group files per user
            for user_id, path in files:
                if os.path.exists(path):
                    user_files[user_id].append(path)

            os.makedirs("processed", exist_ok=True)

            for user_id, file_list in user_files.items():
                name = user_names[user_id]
                merged_path = f"temp_merged_{user_id}_{uuid4().hex}.wav"

                try:
                    if not file_list:
                        continue

                    # Read params from first valid file
                    with wave.open(file_list[0], "rb") as first:
                        params = first.getparams()

                    total_duration = 0.0

                    with wave.open(merged_path, "wb") as output:
                        output.setparams(params)

                        for path in file_list:
                            try:
                                with wave.open(path, "rb") as w:
                                    # Skip mismatched formats
                                    if w.getparams() != params:
                                        logger.warning(
                                            "Param mismatch for %s, skipping", path
                                        )
                                        continue

                                    frames = w.readframes(w.getnframes())
                                    if not frames:
                                        continue

                                    duration = w.getnframes() / w.getframerate()

                                    # Ignore ultra tiny clips (< 0.25 sec)
                                    if duration < 0.25:
                                        continue

                                    output.writeframes(frames)
                                    total_duration += duration

                            except Exception as e:
                                logger.error(
                                    "Error reading wav %s: %s", path, e
                                )

                    # If nothing meaningful was merged → skip
                    if total_duration < 0.3:
                        logger.info(
                            "User %s skipped (merged duration %.2fs)",
                            name,
                            total_duration
                        )
                        continue

                    logger.info(
                        "Merged duration for %s: %.2fs",
                        name,
                        total_duration
                    )

                    text = (
                        self.transcriber
                        .transcribe_file(merged_path)
                        .strip()
                    )

                    if text:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        entry = f"[{timestamp}] {name}: {text}"

                        entries.append((guild.id, entry))
                        transcriptions.append(f"**{name}:** {text}")

                    else:
                        logger.info(
                            "Empty transcription for %s (%.2fs audio)",
                            name,
                            total_duration
                        )

                except Exception as e:
                    logger.error(
                        "process_cut error for user %s: %s",
                        user_id,
                        e
                    )

                finally:
                    # Clean temp merged file
                    if os.path.exists(merged_path):
                        os.remove(merged_path)

                    # Move processed chunks
                    for path in file_list:
                        try:
                            if os.path.exists(path):
                                shutil.move(
                                    path,
                                    os.path.join(
                                        "processed",
                                        os.path.basename(path)
                                    )
                                )
                        except Exception as move_error:
                            logger.error(
                                "Failed to move file %s: %s",
                                path,
                                move_error
                            )

            return transcriptions, entries

        loop = asyncio.get_running_loop()
        transcriptions, entries = await loop.run_in_executor(None, task)

        for g_id, entry in entries:
            self.session_manager.add_entry(g_id, entry)

        return "\n".join(transcriptions)

    # ---------------- SUMMARIZE ----------------

    async def summarize(self, guild_id: int, user_name: str, speakers: list[str] | None = None):
        history = self.session_manager.get_history(guild_id)

        if not history:
            return None

        loop = asyncio.get_running_loop()
        full_text = "\n".join(history)

        logger.info("Summarize called. Transcript length: %d chars", len(full_text))

        logger.info("TEXT SENT TO ANALYST:\n%s", full_text)
        def analysis():
            return self.analyst.smart_summarize(full_text)

        result = await loop.run_in_executor(None, analysis)

        # ---------- fallback if analyst produced empty topics ----------
        if not result or not result.get("topics"):
            logger.warning("Analyst returned no topics — creating fallback topic")
            result = result or {}
            result["topics"] = [
                {
                    "title": "General discussion",
                    "discussions": [
                        {
                            "speaker": "System",
                            "mark": "-",
                            "arguments": ["Transcript quality too low for detailed topic extraction."]
                        }
                    ]
                }
            ]

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
