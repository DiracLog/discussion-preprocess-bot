import pytest
from core.session_manager import SessionManager
from core.orchestrator import ScribeOrchestrator
from ai.ai_manager import initialize_ai
import logging

TEST_AUDIO = "tests/recording_sample/session_337979495787266058_1771089421.wav"

logger = logging.getLogger(__name__)



@pytest.mark.asyncio
async def test_full_pipeline_transcribe_and_summarize():

    # initialize AI (local or api depending on .env)
    ai = initialize_ai()

    session_manager = SessionManager()

    orchestrator = ScribeOrchestrator(
        ai.transcriber,
        ai.analyst,
        ai.memory,
        session_manager
    )

    guild_id = 999
    fake_guild = type("Guild", (), {"id": guild_id, "get_member": lambda self, x: None})()

    # simulate cut processing (single user)
    files = [(123, TEST_AUDIO)]

    text = await orchestrator.process_cut(fake_guild, files)

    assert text is not None
    assert len(session_manager.get_history(guild_id)) > 0

    # now summarize
    result = await orchestrator.summarize(guild_id, "tester")

    assert result is not None

    analysis, log_id = result

    logger.info("TRANSCRIBED TEXT: %s", text)
    logger.info("ANALYSIS: %s", analysis)

    assert "topics" in analysis or "reviews" in analysis
    assert isinstance(log_id, str)
