import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_ctx():
    """
    Creates a fake discord context that can be used in any test
    """
    ctx = MagicMock()
    ctx.guild.id = 123
    ctx.author.display_name = "Tester"
    voice_channel = AsyncMock()
    ctx.author.voice.channel = voice_channel 
    mock_vc = MagicMock()
    
    mock_vc.listen = MagicMock()
    voice_channel.connect.return_value = mock_vc

    ctx.send = AsyncMock()
    ctx.guild.get_member.return_value = MagicMock(display_name="Alice")
    
    return ctx
