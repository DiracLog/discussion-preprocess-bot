import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_interaction():
    interaction = MagicMock()

    interaction.guild_id = 123
    interaction.guild = MagicMock(id=123)

    interaction.user = MagicMock()
    interaction.user.name = "Tester"
    interaction.user.voice = MagicMock()
    interaction.user.voice.channel = AsyncMock()

    interaction.client = MagicMock()

    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()

    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    return interaction
