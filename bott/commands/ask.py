import discord


async def run(
    interaction: discord.Interaction,
    query: str,
    user: discord.Member | None = None
):
    bot = interaction.client
    await bot.ensure_ai_loaded()

    await interaction.response.defer()

    filter_user = user.display_name if user else None
    results = await bot.orchestrator.search(query, filter_user)

    if not results:
        await interaction.followup.send("📭 Nothing found.")
        return

    embed = discord.Embed(title=f"🧠 Recall: {query}")

    for r in results:
        meta = r.get("metadata", {})
        speaker = meta.get("speaker", "?")

        embed.add_field(
            name=speaker,
            value=r.get("text", "")[:200],
            inline=False
        )

    await interaction.followup.send(embed=embed)
