from ..const import MISSING, NotNeeded
from typing import Mapping


class HTTPException(Exception):
    """An error occurred trying to run an HTTP request through the REST API."""

    payload: NotNeeded[dict]
    """The error trace stack of the exception."""
    message: str
    """The message body of the exception."""
    code: int
    """The error code to correlate the exception to."""
    status: int
    """The status code to correlate the exception to."""

    def __init__(
        self,
        status: int,
        headers: Mapping[str, str],
        payload: NotNeeded[dict] = MISSING,
    ):
        """
        Creates a new exception for HTTP requests.

        Parameters
        ----------
        payload : `str`
            The error trace stack of the exception.
        severity : `int`, optional
            The severity level to correlate the exception to. This is treated for logging purposes.
        """
        if payload is not MISSING:
            message = payload.get("message")
            code = payload.get("code")

        self.payload = payload
        self.message = message
        self.code = code
        self.status = status

        # TODO: Add tree flattening

        super.__init__(f"{status} (Discord Error Code: {code}) {message}")


class InvalidToken(Exception):
    """An invalid token was supplied to the Gateway."""


class RateLimited(Exception):
    """
    Too many Gateway commands were sent while being connected.

    You have been disconnected from the Gateway as a result.
    """


class InvalidShard(Exception):
    """An invalid shard was supplied to the Gateway."""


class RequiresSharding(Exception):
    """
    The connection in particular requires sharding, as the guild volume is
    too large to process on one concurrent lay line.
    """


class InvalidIntents(Exception):
    """
    An invalid intent or series of intents were supplied to the Gateway.

    Please check to make sure you've calculated them correctly and are
    using the `|` join operator.
    """


class DisallowedIntents(Exception):
    """
    A disallowed intent or series of intents were supplied to the Gateway.

    You may only supply intents that you have been approved or allowed for.
    If your bot application is pending verification and/or is missing an intent
    checked off in the Developer Portal, this may be the reason why.
    """


class RandomClose(Exception):
    """
    A random close has been initiated by the Gateway.

    These can occur for whatever reason and must be properly handled.
    """
