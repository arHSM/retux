from .misc import TypingStart
from .message import _MessageEvents
from .guild import _GuildEvents


class _EventTable(_MessageEvents, _GuildEvents):
    """
    Stores events from the Gateway for potential use dispatching.
    """

    @classmethod
    def lookup(self, name: str, data: dict):
        if messages := _MessageEvents.lookup(name, data):
            return messages
        elif guilds := _GuildEvents.lookup(name, data):
            return guilds
        if name == "TYPING_START":
            return TypingStart
