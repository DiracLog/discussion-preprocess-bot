import pytest
from unittest.mock import MagicMock, patch
import DiscordBot 
from DiscordBot import join, cut

@pytest.mark.asyncio
async def test_join_command(mock_ctx):
    # 1. Reset state
    DiscordBot.active_sinks = {}
    DiscordBot.session_history = {}

    # 2. Run Command
    mock_ctx.guild.id = 999
    await join(mock_ctx)

    # 3. Assertions
    mock_ctx.author.voice.channel.connect.assert_called_once()
    assert 999 in DiscordBot.active_sinks

@pytest.mark.asyncio
async def test_cut_command(mock_ctx):
    # 1. Setup
    guild_id = 888
    mock_ctx.guild.id = guild_id
    
    # Mock the Sink
    mock_sink = MagicMock()
    mock_sink.save_and_clear_buffers.return_value = [(101, "audio.wav")]
    DiscordBot.active_sinks = {guild_id: mock_sink}
    DiscordBot.session_history = {guild_id: []}

    # Mock the Transcriber
    DiscordBot.transcriber = MagicMock()
    DiscordBot.transcriber.transcribe_file.return_value = "Hello World"

    # Mock Filesystem
    with patch('shutil.move'), patch('os.path.exists', return_value=True):
        await cut(mock_ctx)

    # 2. Assertions
    history = DiscordBot.session_history[guild_id][0]
    assert "Hello World" in history