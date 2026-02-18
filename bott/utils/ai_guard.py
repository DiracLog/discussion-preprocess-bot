import functools
import logging
logger = logging.getLogger(__name__)

def ensure_ai_ready(func):
    """
    Decorator that guarantees AI services are initialized
    before command execution.
    """

    @functools.wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        bot = interaction.client
        logger.info("AI guard triggered for command")
        await bot.ensure_ai_loaded()
        return await func(interaction, *args, **kwargs)

    logger.info("AI guard decorator attached")
    return wrapper