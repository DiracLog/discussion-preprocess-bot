import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.session_manager import SessionManager
from core.orchestrator import ScribeOrchestrator
from typing import Callable, Awaitable

from bott.commands import join, cut, summarize, ask, stop

import logging
logger = logging.getLogger(__name__)

# ---------------- ENV ----------------

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ------------ Bot Class --------------

class ScribeBot(commands.Bot):
    session_manager: SessionManager
    orchestrator: ScribeOrchestrator
    auto_cut_callback: Callable[[int], Awaitable[None]]

    async def ensure_ai_loaded(self):
        if self.orchestrator is not None:
            return

        logger.info("Lazy initializing AI services")
        from ai.ai_manager import initialize_ai

        ai = initialize_ai()

        self.orchestrator = ScribeOrchestrator(
            ai.transcriber,
            ai.analyst,
            ai.memory,
            self.session_manager
        )

        logger.info("AI services initialized")

# ---------------- BOT ----------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = ScribeBot(command_prefix="!", intents=intents)

# ---------------- SERVICES ----------------

bot.session_manager = SessionManager()
bot.orchestrator = None

# ---------------- EVENTS ----------------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.tree.sync()
    print("🌐 Slash commands synced.")

async def auto_cut_callback(guild_id: int):
    await bot.ensure_ai_loaded()

    guild = bot.get_guild(guild_id)
    sink = bot.session_manager.get_sink(guild_id)

    if not guild or not sink:
        return

    files = sink.save_and_clear_buffers()
    await bot.orchestrator.process_cut(guild, files)

bot.auto_cut_callback = auto_cut_callback
# ---------------- COMMAND REGISTRATION ----------------
bot.tree.command(
    name="join",
    description="Join the voice channel and start recording"
)(join.run)

bot.tree.command(
    name="cut",
    description="Transcribe current captured audio"
)(cut.run)

bot.tree.command(
    name="summarize",
    description="Analyze full session and generate report"
)(summarize.run)

bot.tree.command(
    name="ask",
    description="Search stored discussion memory"
)(ask.run)

bot.tree.command(
    name="stop",
    description="Disconnect the bot"
)(stop.run)

# ---------------- RUN ----------------

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not found")

bot.run(TOKEN)
