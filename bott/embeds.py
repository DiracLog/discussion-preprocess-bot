import discord
from datetime import datetime

def create_session_report_embed(full_analysis, channel_members, session_id):
    reviews = full_analysis.get('reviews', [])

    if not reviews:
        return discord.Embed(
            title="⚠️ Analysis Empty",
            description="No topics detected.",
            color=0xff0000
        )

    participants = ", ".join(channel_members) if channel_members else "Unknown"

    embed = discord.Embed(
        title=f"🎙️ Club Meeting Report ({datetime.now().strftime('%Y-%m-%d')})",
        description=f"**Speakers:** {participants}\n**Topics:** {len(reviews)}",
        color=0x3498db
    )

    for r in reviews[:24]:
        title = r.get("title", "Unknown")
        if isinstance(title, list):
            title = title[0]

        mark = r.get("mark", "-")

        arguments = r.get("arguments", [])
        if isinstance(arguments, str):
            arguments = [arguments]

        args = "\n".join(f"• {a}" for a in arguments[:3])

        embed.add_field(
            name=f"{title} ({mark}/10)",
            value=args or "-",
            inline=False
        )

    embed.set_footer(text=f"Session ID: {session_id}")
    return embed
