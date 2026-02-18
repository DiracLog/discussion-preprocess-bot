import os
import shutil
import discord
from discord.ext import voice_recv
from audio.sink import ScribeSink
from bott.utils.ai_guard import ensure_ai_ready

@ensure_ai_ready
async def run(interaction: discord.Interaction):
    bot = interaction.client
    guild_id = interaction.guild_id

    if not interaction.user.voice:
        await interaction.response.send_message("⚠️ Join voice first.", ephemeral=True)
        return

    await interaction.response.defer()

    if not interaction.guild:
        await interaction.followup.send("⚠️ Guild not found.")
        return

    bot.session_manager.clear(guild_id)

    if os.path.exists("temp_pcm"):
        shutil.rmtree("temp_pcm")
    os.makedirs("temp_pcm", exist_ok=True)

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()

    vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)

    sink = ScribeSink()
    bot.session_manager.register_sink(guild_id, sink)
    vc.listen(sink)

    bot.session_manager.reset_cut_timer(
        guild_id,
        bot.auto_cut_callback
    )
    await interaction.followup.send("🎙️ Listening started.")
