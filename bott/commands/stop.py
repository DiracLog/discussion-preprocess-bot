import discord

async def run(interaction: discord.Interaction):
    bot = interaction.client
    guild_id = interaction.guild_id

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
