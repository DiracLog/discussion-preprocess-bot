import os
import discord
from discord import app_commands
from discord.ext import commands, voice_recv
from dotenv import load_dotenv
import time
import wave
import collections
import asyncio
import shutil
from datetime import datetime

# --- IMPORT ENGINES ---
from Recordings import Transcriber
from StructureEngine import StructureAnalyst
from StorageEngine import StorageMind

# Load secrets
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# We still use commands.Bot to manage the connection, but we add the tree logic
bot = commands.Bot(command_prefix='!', intents=intents)

# --- GLOBAL AI STATE ---
print("⏳ Loading AI Engines...")
try:
    transcriber = Transcriber(model_size="medium")
    analyst = StructureAnalyst()
    memory = StorageMind()
    print("✅ AI Systems Online.")
except Exception as e:
    print(f"❌ Error loading AI engines: {e}")
    transcriber = None

# --- SESSION STATE ---
session_history = collections.defaultdict(list)
active_sinks = {}


def create_session_report_embed(full_analysis, channel_members, session_id):
    reviews = full_analysis.get('reviews', [])
    if not reviews:
        return discord.Embed(title="⚠️ Analysis Empty", description="No topics detected.", color=0xff0000)

    participants_str = ", ".join(channel_members) if channel_members else "Unknown"

    embed = discord.Embed(
        title=f"🎙️ Club Meeting Report ({datetime.now().strftime('%Y-%m-%d')})",
        description=f"**Speakers:** {participants_str}\n**Topics Discussed:** {len(reviews)}",
        color=0x3498db
    )

    for i, review in enumerate(reviews):
        if i >= 24:
            embed.add_field(name="...", value="*(More topics in full logs)*", inline=False)
            break

        title = review.get('title', 'Unknown')
        if isinstance(title, list): title = title[0]

        mark = review.get('mark', '-')
        sentiment = review.get('sentiment', 'neutral')
        icon = "🟢" if sentiment == 'positive' else "🔴" if sentiment == 'negative' else "⚪"

        args = review.get('arguments', [])
        if isinstance(args, str): args = [args]

        args_text = ""
        for arg in args[:3]:
            args_text += f"• {arg}\n"
        if not args_text: args_text = "No specific arguments captured."

        field_name = f"{icon} {title} ({mark}/10)"
        embed.add_field(name=field_name, value=args_text, inline=False)

    embed.set_footer(text=f"Session ID: {session_id}")
    return embed


class ScribeSink(voice_recv.AudioSink):
    def __init__(self):
        super().__init__()
        print("🎧 Scribe Listening...")
        self.user_buffers = collections.defaultdict(list)
        self.packet_counters = collections.defaultdict(int)
        self.decoders = {}
        if not os.path.exists("temp_pcm"): os.makedirs("temp_pcm")

    def wants_opus(self):
        return True

    def write(self, user, data):
        if user is None: return
        user_id = user.id

        if user_id not in self.decoders:
            self.decoders[user_id] = discord.opus.Decoder()

        try:
            packet_bytes = getattr(data.packet, 'decrypted_data', data.packet.payload)
            pcm = self.decoders[user_id].decode(packet_bytes, fec=True)
            self.user_buffers[user_id].append(pcm)
            self.packet_counters[user_id] += 1

            if self.packet_counters[user_id] >= 500:
                self.flush_to_disk(user_id)
        except Exception:
            pass

    def flush_to_disk(self, user_id):
        if not self.user_buffers[user_id]: return
        filename = f"temp_pcm/stream_{user_id}.pcm"
        with open(filename, 'ab') as f:
            f.write(b''.join(self.user_buffers[user_id]))
        self.user_buffers[user_id] = []
        self.packet_counters[user_id] = 0

    def cleanup(self):
        for uid in list(self.user_buffers.keys()):
            self.flush_to_disk(uid)

    def save_and_clear_buffers(self):
        self.cleanup()
        saved_files = []
        timestamp = int(time.time())

        for filename in os.listdir("temp_pcm"):
            if not filename.endswith(".pcm"): continue
            try:
                user_id = int(filename.split("_")[1].split(".")[0])
                pcm_path = os.path.join("temp_pcm", filename)
                wav_path = f"recordings/session_{user_id}_{timestamp}.wav"

                if not os.path.exists("recordings"): os.makedirs("recordings")

                with open(pcm_path, 'rb') as pcm_file:
                    pcm_data = pcm_file.read()
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(2)
                        wf.setsampwidth(2)
                        wf.setframerate(48000)
                        wf.writeframes(pcm_data)

                os.remove(pcm_path)
                saved_files.append((user_id, wav_path))
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        return saved_files


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    # SYNC COMMANDS WITH DISCORD
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} Slash Commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


# --- SLASH COMMANDS START HERE ---

@bot.tree.command(name="join", description="Join the voice channel to start the session")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        guild_id = interaction.guild_id

        # Defer allows us time to connect without timing out
        await interaction.response.defer()

        session_history[guild_id] = []
        if os.path.exists("temp_pcm"):
            shutil.rmtree("temp_pcm")
            os.makedirs("temp_pcm")

        try:
            vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
            new_sink = ScribeSink()
            active_sinks[guild_id] = new_sink
            vc.listen(new_sink)

            await interaction.followup.send(f"🎙️ Connected to **{channel.name}** and listening!")
        except Exception as e:
            await interaction.followup.send(f"❌ Connection error: {e}")
    else:
        await interaction.response.send_message("⚠️ You must be in a voice channel first.", ephemeral=True)


@bot.tree.command(name="cut", description="Stop the current segment, transcribe it, and add to logs")
async def cut(interaction: discord.Interaction):
    # Defer immediately because transcription takes time
    await interaction.response.defer()

    guild_id = interaction.guild_id
    sink = active_sinks.get(guild_id)

    if not sink:
        await interaction.followup.send("⚠️ I am not listening. Run `/join` first.")
        return

    # Trigger save
    files_to_process = sink.save_and_clear_buffers()

    if not files_to_process:
        await interaction.followup.send("🔇 No audio detected since last cut.")
        return

    # Process in background
    loop = asyncio.get_running_loop()

    def process_files():
        results_text = []
        for user_id, filename in files_to_process:
            try:
                member = interaction.guild.get_member(user_id)
                display_name = member.display_name if member else f"User_{user_id}"

                text = transcriber.transcribe_file(filename)
                if text.strip():
                    time_str = datetime.now().strftime("%H:%M:%S")
                    log_entry = f"[{time_str}] {display_name}: {text}"
                    session_history[guild_id].append(log_entry)
                    results_text.append(f"**{display_name}:** {text}")

                if not os.path.exists("processed"): os.makedirs("processed")
                shutil.move(filename, os.path.join("processed", os.path.basename(filename)))
            except Exception as e:
                print(f"❌ Error: {e}")
        return "\n".join(results_text)

    new_text = await loop.run_in_executor(None, process_files)

    if new_text:
        # Send transcript to channel
        # If text is too long for one message (2000 chars), we chunk it
        if len(new_text) > 1900:
            filename = f"transcript_part_{int(time.time())}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(new_text)
            await interaction.followup.send("📄 Segment too long, uploading as file:", file=discord.File(filename))
            os.remove(filename)
        else:
            await interaction.followup.send(f"📝 **Segment Transcript:**\n{new_text}")
    else:
        await interaction.followup.send("🤷‍♂️ Audio captured, but no speech detected (silence/noise).")


@bot.tree.command(name="ask", description="Search the book club memory")
@app_commands.describe(query="What specific topic or argument to look for",
                       user="Filter by specific speaker (Optional)")
async def ask(interaction: discord.Interaction, query: str, user: discord.Member = None):
    await interaction.response.defer()

    target_user_name = user.display_name if user else None

    loop = asyncio.get_running_loop()

    def run_search():
        return memory.search_memory(query_text=query, n_results=3, filter_user=target_user_name)

    try:
        results = await loop.run_in_executor(None, run_search)

        if not results:
            await interaction.followup.send(f"📭 No memories found for: '{query}'")
            return

        embed = discord.Embed(title=f"🧠 Recall: '{query}'", color=0xF1C40F)
        if target_user_name:
            embed.set_footer(text=f"Filtered for speaker: {target_user_name}")

        for i, res in enumerate(results):
            text = res.get('text', 'No text')
            meta = res.get('metadata', {})
            date = meta.get('date', 'Unknown')
            speakers = meta.get('speaker', 'Unknown')  # Note: Check if key is 'speaker' or 'speaker_id' in your DB

            embed.add_field(
                name=f"Result {i + 1} ({date})",
                value=f"**{speakers}:** {text[:200]}...",
                inline=False
            )

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Search Error: {e}")


@bot.tree.command(name="summarize", description="End session and generate full meeting minutes")
async def summarize(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    history = session_history.get(guild_id, [])

    if not history:
        await interaction.response.send_message("📭 Transcript is empty. Did you run `/cut`?", ephemeral=True)
        return

    await interaction.response.defer()
    await interaction.followup.send("🧠 Analyzing full session... (This takes 30-60s)")

    full_transcript = "\n".join(history)

    # Get members currently in voice channel for metadata
    if interaction.user.voice:
        active_members = [m.display_name for m in interaction.user.voice.channel.members if not m.bot]
    else:
        active_members = ["Unknown Group"]

    loop = asyncio.get_running_loop()

    def run_analysis():
        # Using smart_summarize for map-reduce capabilities
        return analyst.smart_summarize(full_transcript)

    try:
        analysis_result = await loop.run_in_executor(None, run_analysis)
        reviews = analysis_result.get('reviews', [])

        if not reviews:
            await interaction.followup.send("⚠️ No specific topics/reviews found in the discussion.")
            return

        # Cold Storage
        log_id = memory.save_log_to_disk(
            transcript=full_transcript,
            analysis=analysis_result,
            user_name=interaction.user.name
        )

        def save_vectors():
            for review in reviews:
                memory.save_analysis(
                    analysis_json=review,
                    original_transcription=full_transcript,
                    speaker_id=", ".join(active_members),
                    full_log_id=log_id
                )

        await loop.run_in_executor(None, save_vectors)

        embed = create_session_report_embed(
            full_analysis=analysis_result,
            channel_members=active_members,
            session_id=log_id
        )
        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Analysis failed: {e}")
        await interaction.followup.send(f"❌ Critical Analysis Error: {e}")


@bot.tree.command(name="stop", description="Disconnect bot and cleanup")
async def stop(interaction: discord.Interaction):
    guild_id = interaction.guild_id

    if interaction.guild.voice_client:
        if guild_id in active_sinks:
            active_sinks[guild_id].cleanup()
            del active_sinks[guild_id]

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Disconnected.")
    else:
        await interaction.response.send_message("⚠️ I am not in a voice channel.", ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)