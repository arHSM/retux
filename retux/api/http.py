from enum import Enum
from json import dumps, loads
from logging import INFO, getLogger
from mimetypes import guess_type
from sys import version_info
from typing import IO, Any, Literal, Protocol

from attrs import define, field
from httpx import AsyncClient
from httpx import __version__ as __http_version__
from trio import Event, sleep

from ..const import MISSING, NotNeeded, __api_url__, __repo_url__, __version__
from .error import HTTPException

logger = getLogger(__name__)

__all__ = ("HTTPClient", "File")


class Endpoint(Enum):
    GET_GATEWAY_BOT = "/gateway/bot"
    GET_GUILD_MEMBER = "/guilds/{guild_id}/members/{user_id}"

    def format(self, **kwargs) -> str:
        return self.value.format(**kwargs)


def _get_bucket_identifier(
    route: str,
    guild_id: NotNeeded[str] = MISSING,
    channel_id: NotNeeded[str] = MISSING,
    shared: NotNeeded[str] = MISSING,
):
    return (
        f"{channel_id}:{guild_id}:{route}"
        if shared is MISSING
        else f"{channel_id}:{guild_id}:{shared}"
    )


@define(slots=False)
class _Limit:
    """Represents a bucket that exists for a route."""

    event: Event = field(default=Event())
    """The asynchronous event associated to the bucket, used for blocking conditions."""
    reset_after: float = field(default=0.0)
    """The time remaining before the event may be reset. Defaults to `0.0`."""


class File:
    name: str
    path: str
    description: str
    mime: str
    fd: NotNeeded[bytes | IO[bytes]]

    def __init__(
        self,
        name: str,
        path: str,
        description: NotNeeded[str] = MISSING,
        fd: NotNeeded[bytes | IO[bytes]] = MISSING,
    ) -> None:
        self.name = name
        self.path = path
        self.description = "" if description is MISSING else description
        mime, _ = guess_type(path)
        self.mime = mime or "application/octet-stream"
        self.fd = fd

    def get(self) -> bytes | IO[bytes]:
        if self.fd is MISSING:
            self.fd = open(self.path, "rb")
        return self.fd

    def close(self) -> None:
        if self.fd is not MISSING and not isinstance(self.fd, bytes):
            self.fd.close()


class HTTPProtocol(Protocol):
    def __init__(self, token: str):
        ...

    async def request(
        self,
        method: Literal["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
        route: str | Endpoint,
        json: NotNeeded[Any] = MISSING,
        query: NotNeeded[dict[str, str]] = MISSING,
        files: NotNeeded[list[File]] = MISSING,
        reason: NotNeeded[str] = MISSING,
        retries: NotNeeded[int] = MISSING,
    ):
        ...


class HTTPClient(HTTPProtocol):
    """
    Represents a connection to Discord's REST API. The most common use case
    of the Discord API will be providing a service, or access to a platform
    through the OAuth2 API.

    Attributes
    ----------
    token : `str`
        The bot's token.
    _client : `AsyncClient`
        HTTPX AsyncClient instance.
    _global_rate_limit : `_Limit`
        The global rate limit state.
    _rate_limits : `dict[str, _Limit]`
        The rate limits currently stored.
    """

    __slots__ = ("token", "_client", "_headers")
    token: str
    """The bot's token."""
    _client: AsyncClient
    """HTTPX AsyncClient instance."""
    _global_rate_limit: _Limit = _Limit()
    """The global rate limit state."""
    _rate_limits: dict[str, _Limit] = {}
    """The rate limits currently stored."""

    def __init__(self, token: str):
        """
        Creates a new connection to the REST API.

        Parameters
        ----------
        token : `str`
            The bot's token to connect with.
        """
        self.token = token
        headers = {
            "Authorization": f"Bot {self.token}",
            "User-Agent": f"DiscordBot ({__repo_url__} {__version__}) "
            f"Python/{version_info[0]}.{version_info[1]} "
            f"httpx/{__http_version__}",
        }
        self._client = AsyncClient(headers=headers, http2=True, base_url=__api_url__)

    async def request(
        self,
        method: Literal["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"],
        route: str | Endpoint,
        json: NotNeeded[Any] = MISSING,
        query: NotNeeded[dict[str, str]] = MISSING,
        files: NotNeeded[list[File]] = MISSING,
        reason: NotNeeded[str] = MISSING,
        retries: NotNeeded[int] = MISSING,
        **kwargs,
    ):
        route = route.format(**kwargs)
        reqkwargs = {}

        if query is not MISSING:
            reqkwargs["params"] = query

        if reason is not MISSING:
            reqkwargs["headers"] = {"X-Audit-Log-Reason": reason}

        if method != "GET":
            if files is not MISSING:
                reqkwargs["data"] = {"payload_json": dumps(json)}
                reqkwargs["files"] = []
                for (idx, file) in enumerate(files.__iter__()):
                    reqkwargs["files"].append((f"files[{idx}]", (file.name, file.get(), file.mime)))
            else:
                reqkwargs["json"] = json

        retry_attempts = 1 if retries is MISSING else retries

        request = self._client.build_request(method, route, **reqkwargs)

        if self._global_rate_limit.event.is_set() and self._global_rate_limit.reset_after != 0:
            logger.warning(
                f"There is still a global rate limit ongoing. Trying again in {self._global_rate_limit.reset_after}s."
            )
            await self._global_rate_limit.event.wait(self._global_rate_limit.reset_after)
            self._global_rate_limit.reset_after = 0.0
        elif self._global_rate_limit.reset_after == 0.0:
            self._global_rate_limit.event = Event()

        bucket_identifier = _get_bucket_identifier(
            route, kwargs.get("guild_id", MISSING), kwargs.get("channel_id", MISSING)
        )
        rate_limit = self._rate_limits.get(bucket_identifier)
        if rate_limit:
            if rate_limit.event.is_set() and rate_limit.reset_after != 0:
                logger.warning(
                    f"The current bucket {bucket_identifier} is still under a rate limit. Trying again in {rate_limit.reset_after}s."
                )
                await rate_limit.event.wait(rate_limit.reset_after)
                rate_limit.reset_after = 0.0
            elif rate_limit.reset_after == 0.0:
                rate_limit.event = Event()
        else:
            self._rate_limits[bucket_identifier] = _Limit()

        for attempt in range(retry_attempts):
            try:
                response = await self._client.send(request)

                if response.is_error:
                    await response.aclose()
                    raise HTTPException(response.status_code, response.headers)

                payload = (
                    response.text
                    if response.headers.get("Content-Type") != "application/json"
                    else response.json()
                )

                if response.status_code == 429:
                    reset_after = response.headers.get("X-RateLimit-Reset-After", 0.0)
                    if bool(response.headers.get("X-RateLimit-Global")):
                        logger.warning(
                            f"A global rate limit has occured. Locking down future requests for {reset_after}s."
                        )
                        self._global_rate_limit.reset_after = reset_after
                        self._global_rate_limit.set()
                    else:
                        logger.warning(
                            f"A route-based rate limit has occured. Locking down future requests for {reset_after}s."
                        )
                        rate_limit.reset_after = reset_after
                        rate_limit.event.set()
                if response.headers.get("X-RateLimit-Remaining", 0) == 0:
                    logger.warning(
                        f"We've reached the maximum number of requests possible. Locking down future requests for {reset_after}s."
                    )
                    await sleep(reset_after)

                return payload

            except OSError as err:
                if attempt <= 1 and err.errno in {54, 10054}:
                    await sleep(5)
            except Exception as err:
                logger.info(err)
                # Propogate error for further handling (?)
                raise

        if files is not MISSING:
            for file in files.__iter__():
                file.close()

    async def aclose(self) -> None:
        return await self._client.aclose()
