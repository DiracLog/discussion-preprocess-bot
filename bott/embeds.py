import discord
from datetime import datetime

def create_session_report_embed(full_analysis, channel_members, session_id):
    topics = full_analysis.get("topics", [])

    if not topics:
        return discord.Embed(
            title="⚠️ Analysis Empty",
            description="No topics detected.",
            color=0xff0000
        )

    participants = ", ".join(channel_members) if channel_members else "Unknown"

    embed = discord.Embed(
        title=f"🎙️ Club Meeting Report ({datetime.now().strftime('%Y-%m-%d')})",
        description=f"**Speakers:** {participants}\n**Topics:** {len(topics)}",
        color=0x3498db
    )

    field_counter = 0

    for topic in topics:
        title = topic.get("title", "Unknown")
        if isinstance(title, list):
            title = title[0]

        discussions = topic.get("discussions", [])

        for discussion in discussions:
            if field_counter >= 24:
                embed.add_field(
                    name="...",
                    value="*(More topics in full logs)*",
                    inline=False
                )
                embed.set_footer(text=f"Session ID: {session_id}")
                return embed

            speaker = discussion.get("speaker", "Unknown")
            mark = discussion.get("mark", "-")

            arguments = discussion.get("arguments", [])
            if isinstance(arguments, str):
                arguments = [arguments]

            shown = arguments[:5]
            args = "\n".join(f"• {a}" for a in shown)

            if len(arguments) > 5:
                args += f"\n… and {len(arguments) - 5} more"

            embed.add_field(
                name=f"{title} — {speaker}",
                value=f"**Mark:** {mark}/10\n{args or '-'}",
                inline=False
            )

            field_counter += 1

    embed.set_footer(text=f"Session ID: {session_id}")
    return embed
