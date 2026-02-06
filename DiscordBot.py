import os
import discord
from discord.ext import commands, voice_recv
from dotenv import load_dotenv
import time
import wave
import collections
import asyncio
import shutil
from datetime import datetime

# --- IMPORT ENGINES ---
# (Assuming these are your local files)
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

bot = commands.Bot(command_prefix='!', intents=intents)

# --- GLOBAL AI STATE ---
print("Loading models...")
try:
    transcriber = Transcriber()
    analyst = StructureAnalyst()
    memory = StorageMind()
except Exception as e:
    print(f"❌ Error loading AI engines: {e}")
    transcriber = None

# --- SESSION STATE (Multi-Server Safe) ---
# Key: Guild ID (int), Value: List of strings
session_history = collections.defaultdict(list)

# Key: Guild ID (int), Value: ScribeSink Instance
active_sinks = {}


def create_session_report_embed(full_analysis, channel_members, session_id):
    """
    Builds a single 'Meeting Minutes' style report.
    """
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

        # Ensure temp directory exists
        if not os.path.exists("temp_pcm"):
            os.makedirs("temp_pcm")

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

            # Flush to disk every 500 packets to save RAM
            if self.packet_counters[user_id] >= 500:
                self.flush_to_disk(user_id)

        except Exception as e:
            # In high-load voice, silencing errors prevents console spam
            pass

    def flush_to_disk(self, user_id):
        """Moves RAM data to the specific user's temporary file"""
        if not self.user_buffers[user_id]: return

        filename = f"temp_pcm/stream_{user_id}.pcm"
        with open(filename, 'ab') as f:
            f.write(b''.join(self.user_buffers[user_id]))

        self.user_buffers[user_id] = []
        self.packet_counters[user_id] = 0

    def cleanup(self):
        """
        REQUIRED: Called when the sink is destroyed or disconnected.
        We ensure all remaining buffers are flushed.
        """
        print("🧹 Cleaning up ScribeSink...")
        for uid in list(self.user_buffers.keys()):
            self.flush_to_disk(uid)

    def save_and_clear_buffers(self):
        """
        Converts PCM temp files to WAV and returns a list of (user_id, filepath).
        """
        saved_files = []
        timestamp = int(time.time())

        # 1. Flush any remaining data in RAM
        self.cleanup()

        # 2. Convert all temp PCM files to WAV
        for filename in os.listdir("temp_pcm"):
            if not filename.endswith(".pcm"): continue

            try:
                # filename format: stream_{user_id}.pcm
                user_id_str = filename.split("_")[1].split(".")[0]
                user_id = int(user_id_str)

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

                # Remove the temp file so it doesn't corrupt the next session
                os.remove(pcm_path)
                saved_files.append((user_id, wav_path))

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

        return saved_files


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')


@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        guild_id = ctx.guild.id

        # 1. Reset History for this specific server
        session_history[guild_id] = []

        # 2. Safety cleanup of temp files before starting
        # This prevents "appending" to audio from a previous crashed session
        if os.path.exists("temp_pcm"):
            shutil.rmtree("temp_pcm")
            os.makedirs("temp_pcm")

        try:
            vc = await channel.connect(cls=voice_recv.VoiceRecvClient)

            # 3. Create Sink and store it mapped to this Guild ID
            new_sink = ScribeSink()
            active_sinks[guild_id] = new_sink

            vc.listen(new_sink)
            await ctx.send(f"Listening in {channel.name}!")
        except Exception as e:
            await ctx.send(f"Error: {e}")
    else:
        await ctx.send("Author of command must be in voice chat.")


@bot.command()
async def cut(ctx):
    guild_id = ctx.guild.id

    # Retrieve the sink specific to this server
    sink = active_sinks.get(guild_id)

    if not sink:
        await ctx.send("Not listening here. Run !join first.")
        return

    await ctx.send("Cutting and transcribing...")

    # OPTIONAL: Pause listening to ensure file locks are released
    # if ctx.voice_client: ctx.voice_client.stop_listening()

    files_to_process = sink.save_and_clear_buffers()

    if not files_to_process:
        await ctx.send("⚠️ Silence detected.")
        # Resume listening if you paused
        # if ctx.voice_client: ctx.voice_client.listen(sink)
        return

    loop = asyncio.get_running_loop()

    def process_files():
        results_text = []
        for user_id, filename in files_to_process:
            try:
                # Resolving the User ID to a Name
                member = ctx.guild.get_member(user_id)
                display_name = member.display_name if member else f"User_{user_id}"

                text = transcriber.transcribe_file(filename)

                if text.strip():
                    time_str = datetime.now().strftime("%H:%M:%S")

                    # Log to server-specific history
                    log_entry = f"[{time_str}] {display_name}: {text}"
                    session_history[guild_id].append(log_entry)

                    results_text.append(f"**{display_name}:** {text}")

                if not os.path.exists("processed"): os.makedirs("processed")
                shutil.move(filename, os.path.join("processed", os.path.basename(filename)))

            except Exception as e:
                print(f"❌ Error: {e}")
        return "\n".join(results_text)

    new_text = await loop.run_in_executor(None, process_files)

    # Resume listening immediately after processing is done
    # if ctx.voice_client and not ctx.voice_client.is_listening():
    #     ctx.voice_client.listen(sink)

    if new_text:
        await ctx.send("Speech was transcribed")
    else:
        await ctx.send("No speech detected")

@bot.command()
async def ask(ctx, *, query):
    """
        Searches memory. You can tag a user to filter by them.
        Usage: !ask @Alice arguments about SQL
        """
    target_user = None
    message = ctx.message.mentions[0]
    # 1. Check if a user was mentioned (tagged) in the message
    if ctx.message.mentions:
        target_user = message.display_name
        query = query.replace(message.mention, "").strip()


    loop = asyncio.get_running_loop()

    def run_search():
        # We pass the 'target_user' to the search function
        return memory.search_memory(query_text=query, n_results=3, filter_user=target_user)

    try:
        results = await loop.run_in_executor(None, run_search)

        if not results:
            print("No relevant memories found")
            return

        embed = discord.Embed(
            title=f"🧠 Recall: '{query}'",
            color=0xF1C40F
        )

        if target_user:
            embed.set_footer(text=f"Filtered for speaker: {target_user}")

        for i, res in enumerate(results):
            text = res.get('text', 'No text')
            meta = res.get('metadata', {})
            date = meta.get('date', 'Unknown')
            speakers = meta.get('speaker_id', 'Unknown')

            # Show the result
            embed.add_field(
                name=f"Topic {i + 1} ({date})",
                value=f"**Speakers:** {speakers}\n📝 {text[:200]}...",
                inline=False
            )

        await ctx.send(embed=embed)

    except Exception as e:
        print(f"Search failed: {e}")



@bot.command()
async def summarize(ctx):
    guild_id = ctx.guild.id
    history = session_history.get(guild_id, [])

    if not history:
        await ctx.send("Transcript empty.")
        return

    await ctx.send("Analyzing full session...")

    full_transcript = "\n".join(history)
    active_members = [m.display_name for m in ctx.author.voice.channel.members if not m.bot]

    loop = asyncio.get_running_loop()

    def run_analysis():
        return analyst.extract_structure(full_transcript)

    try:
        analysis_result = await loop.run_in_executor(None, run_analysis)
        reviews = analysis_result.get('reviews', [])

        if not reviews:
            await ctx.send("No topics found in discussion.")
            return

        # Cold Storage
        log_id = memory.save_log_to_disk(
            transcript=full_transcript,
            analysis=analysis_result,
            user_name=ctx.author.name
        )

        await ctx.send(f"Saving {len(reviews)} memories...")

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
        await ctx.send(embed=embed)

    except Exception as e:
        print(f"Analysis failed: {e}")
        await ctx.send(f"Critical Error: {e}")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        guild_id = ctx.guild.id

        # Cleanup Sink
        if guild_id in active_sinks:
            active_sinks[guild_id].cleanup()
            del active_sinks[guild_id]

        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected.")


if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)