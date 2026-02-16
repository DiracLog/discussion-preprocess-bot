import collections
import logging
from typing import Dict, List, Optional, Callable, Awaitable
import asyncio
from audio.sink import ScribeSink

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        # guild_id -> transcript entries
        self.session_history: Dict[int, List[str]] = collections.defaultdict(list)

        # guild_id -> active ScribeSink
        self.active_sinks: Dict[int, ScribeSink] = {}

        self.cut_timers: Dict[int, asyncio.Task] = {}

    # -------- transcript --------

    def add_entry(self, guild_id: int, text: str) -> None:
        self.session_history[guild_id].append(text)

    def get_history(self, guild_id: int) -> List[str]:
        # return copy to prevent accidental external mutation
        return list(self.session_history.get(guild_id, []))

    def clear(self, guild_id: int) -> None:
        self.session_history[guild_id].clear()

    # -------- sinks --------

    def register_sink(self, guild_id: int, sink: ScribeSink) -> None:
        self.active_sinks[guild_id] = sink

    def get_sink(self, guild_id: int) -> Optional[ScribeSink]:
        return self.active_sinks.get(guild_id)

    def remove_sink(self, guild_id: int) -> None:
        self.cancel_cut_timer(guild_id)

        sink = self.active_sinks.pop(guild_id, None)

        if sink:
            try:
                sink.cleanup()
            except Exception as e:
                logger.error(f"Sink cleanup failed: {e}")

    # -------- auto-cut timers --------

    def reset_cut_timer(
            self,
            guild_id: int,
            callback: Callable[[int], Awaitable[None]],
            delay_seconds: int = 1800
    ):
        """
        Resets inactivity timer for automatic cut.
        """

        self.cancel_cut_timer(guild_id)

        async def timer():
            await asyncio.sleep(delay_seconds)
            await callback(guild_id)

        self.cut_timers[guild_id] = asyncio.create_task(timer())

    def cancel_cut_timer(self, guild_id: int):
        task = self.cut_timers.pop(guild_id, None)
        if task:
            task.cancel()

    def cleanup_all(self) -> None:
        for gid in list(self.active_sinks.keys()):
            self.remove_sink(gid)

        for task in self.cut_timers.values():
            task.cancel()
        self.cut_timers.clear()
