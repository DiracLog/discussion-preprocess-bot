import collections
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self):
        # guild_id -> transcript entries
        self.session_history: Dict[int, List[str]] = collections.defaultdict(list)

        # guild_id -> active ScribeSink
        self.active_sinks: Dict[int, object] = {}

    # -------- transcript --------

    def add_entry(self, guild_id: int, text: str) -> None:
        self.session_history[guild_id].append(text)

    def get_history(self, guild_id: int) -> List[str]:
        # return copy to prevent accidental external mutation
        return list(self.session_history.get(guild_id, []))

    def clear(self, guild_id: int) -> None:
        self.session_history[guild_id].clear()

    # -------- sinks --------

    def register_sink(self, guild_id: int, sink: object) -> None:
        self.active_sinks[guild_id] = sink

    def get_sink(self, guild_id: int) -> Optional[object]:
        return self.active_sinks.get(guild_id)

    def remove_sink(self, guild_id: int) -> None:
        sink = self.active_sinks.pop(guild_id, None)

        if sink:
            try:
                sink.cleanup()
            except Exception as e:
                logger.error(f"Sink cleanup failed: {e}")

    def cleanup_all(self) -> None:
        for gid in list(self.active_sinks.keys()):
            self.remove_sink(gid)
