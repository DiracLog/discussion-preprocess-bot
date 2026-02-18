import functools


def ensure_ai_ready(func):
    """
    Decorator that guarantees AI services are initialized
    before command execution.
    """

    @functools.wraps(func)
    async def wrapper(interaction, *args, **kwargs):
        bot = interaction.client
        await bot.ensure_ai_loaded()
        return await func(interaction, *args, **kwargs)

    return wrapper