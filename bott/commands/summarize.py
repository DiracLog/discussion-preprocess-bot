import discord
from bott.embeds import create_session_report_embed


async def run(interaction: discord.Interaction):
    bot = interaction.client
    guild_id = interaction.guild_id

    await interaction.response.defer()
    await interaction.followup.send("🧠 Analyzing session...")

    if not interaction.guild:
        await interaction.followup.send("⚠️ Guild not found.")
        return

    members = []
    if interaction.user.voice:
        members = [
            m.display_name
            for m in interaction.user.voice.channel.members
            if not m.bot
        ]

    result = await bot.orchestrator.summarize(
        guild_id,
        interaction.user.name,
        members
    )

    if not result:
        await interaction.followup.send("📭 Transcript empty.")
        return

    analysis, log_id = result

    embed = create_session_report_embed(analysis, members, log_id)
    await interaction.followup.send(embed=embed)
