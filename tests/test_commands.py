import pytest
from unittest.mock import MagicMock, AsyncMock

from bott.commands import join, cut


@pytest.mark.asyncio
async def test_join_command(mock_interaction):
    bot = MagicMock()
    mock_interaction.client = bot
    mock_interaction.guild_id = 999

    # session manager mock
    bot.session_manager = MagicMock()

    # voice connect mock
    voice_channel = AsyncMock()
    mock_interaction.user.voice.channel = voice_channel
    voice_client = MagicMock()
    voice_channel.connect.return_value = voice_client

    await join.run(mock_interaction)

    voice_channel.connect.assert_called_once()
    bot.session_manager.register_sink.assert_called_once()


@pytest.mark.asyncio
async def test_cut_command(mock_interaction):
    bot = MagicMock()
    mock_interaction.client = bot
    mock_interaction.guild_id = 888
    mock_interaction.guild = MagicMock()

    # fake sink
    mock_sink = MagicMock()
    mock_sink.save_and_clear_buffers.return_value = [(101, "audio.wav")]

    bot.session_manager = MagicMock()
    bot.session_manager.get_sink.return_value = mock_sink

    bot.orchestrator = MagicMock()
    bot.orchestrator.process_cut = AsyncMock(return_value="Hello World")

    await cut.run(mock_interaction)

    bot.orchestrator.process_cut.assert_called_once()
    mock_interaction.followup.send.assert_called()
