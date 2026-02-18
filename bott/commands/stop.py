import discord
from bott.utils.ai_guard import ensure_ai_ready

@ensure_ai_ready
async def run(interaction: discord.Interaction):
    bot = interaction.client
    guild_id = interaction.guild_id

    await bot.ensure_ai_loaded(bot)
    if not interaction.guild:
        await interaction.response.send_message("⚠️ Guild not found.", ephemeral=True)
        return

    bot.session_manager.remove_sink(guild_id)

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        msg = "👋 Disconnected."
    else:
        msg = "⚠️ I am not connected."

    await interaction.response.send_message(msg)
