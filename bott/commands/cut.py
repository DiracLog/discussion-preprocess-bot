import os
import time
import discord
from bott.utils.ai_guard import ensure_ai_ready

@ensure_ai_ready
async def run(interaction: discord.Interaction):
    bot = interaction.client
    guild_id = interaction.guild_id

    await interaction.response.defer()
    await bot.ensure_ai_loaded(bot)

    if not interaction.guild:
        await interaction.followup.send("⚠️ Guild not found.")
        return

    sink = bot.session_manager.get_sink(guild_id)

    if not sink:
        await interaction.followup.send("⚠️ Not listening.")
        return

    files = sink.save_and_clear_buffers()

    text = await bot.orchestrator.process_cut(interaction.guild, files)

    bot.session_manager.reset_cut_timer(
        guild_id,
        bot.auto_cut_callback
    )

    if not text:
        await interaction.followup.send("🔇 No speech detected.")
        return

    if len(text) > 1900:
        fname = f"segment_{int(time.time())}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)
        await interaction.followup.send(file=discord.File(fname))
        os.remove(fname)
    else:
        await interaction.followup.send(f"📝 {text}")
