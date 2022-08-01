from ..bot import Bot
from ...api.http import _Route, _RouteMethod
from .editable import Editable

from attrs import asdict

__all__ = ["Respondable"]


class Respondable(Editable):
    """
    A mixin for objects with send/edit/delete methods.

    Methods
    -------
    respond() : `dict`
        Executes a `respond` action to Discord with the given path and keyword arguments.
    send() : `dict`
        An alias of the `respond()` method.
    """

    async def respond(self, bot: Bot, path: str, **kwargs) -> dict:
        """
        Executes a `respond` action to Discord with the given path and keyword arguments.

        Parameters
        ----------
        bot : `retux.Bot`
            The instance of the bot.
        path : `str`
            The path to the endpoint of the Discord API.
        **kwargs : `dict`
            The data to include in the request.

        Returns
        -------
        `dict`
            The data of the interaction response returned by Discord.
        """

        route = _Route(method=_RouteMethod.POST, path=path)

        payload = {}
        for key, value in kwargs.items():
            if hasattr(value, "__slots__"):
                payload[key] = asdict(
                    value, filter=lambda _name, _value: _name.name not in {"_bot", "bot"}
                )
            else:
                payload[key] = value

        return await bot.http.request(route, payload)

    async def send(self, bot: Bot, path: str, **kwargs) -> dict:
        """An alias of the `respond()` method."""
        return await self.respond(bot, path, **kwargs)
