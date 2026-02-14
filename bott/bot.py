import os
import discord
from discord.ext import commands
from dotenv import load_dotenv


from ai.ai_manager import initialize_ai
from core.session_manager import SessionManager
from core.orchestrator import ScribeOrchestrator

from bott.commands import join, cut, summarize, ask, stop

# ---------------- ENV ----------------

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ---------------- BOT ----------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- SERVICES ----------------

ai = initialize_ai()
session_manager = SessionManager()

orchestrator = ScribeOrchestrator(
    ai.transcriber,
    ai.analyst,
    ai.memory,
    session_manager
)

bot.session_manager: SessionManager = session_manager
bot.orchestrator: ScribeOrchestrator = orchestrator

# ---------------- EVENTS ----------------

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.tree.sync()
    print("🌐 Slash commands synced.")

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
