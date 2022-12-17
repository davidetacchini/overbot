from typing import Any

import aiohttp

import config  # pyright: reportMissingImports=false

from .exceptions import (
    NotFound,
    BadRequest,
    TooManyAccounts,
    UnexpectedError,
    ServiceUnavailable,
    InternalServerError,
)


class Request:

    __slots__ = ("platform", "username", "username_l")

    def __init__(self, platform: str, username: str) -> None:
        self.platform = platform
        self.username = username
        self.username_l: str = username.lower()

    @property
    def account_url(self) -> str:
        return config.overwatch["account"] + "/" + self.username.replace("#", "%23") + "/"

    async def _resolve_name(self, players: list[dict[str, Any]]) -> str:
        if len(players) == 1:
            try:
                return players[0]["battleTag"].replace("#", "-")
            except Exception:
                raise InternalServerError()
        elif len(players) > 1:
            for player in players:
                if self.username_l == player["battleTag"].lower():
                    return player["battleTag"]
            raise TooManyAccounts(self.platform, self.username, len(players))
        else:
            # return the username and let `resolve_response` handle it
            return self.username

    async def _get_name(self) -> None | str:
        async with aiohttp.ClientSession() as s:
            async with s.get(self.account_url) as r:
                try:
                    name = await r.json()
                except Exception:
                    raise UnexpectedError()
                else:
                    return await self._resolve_name(name)

    async def _get_url(self) -> str:
        name = await self._get_name()
        return f"{config.base_url}/{self.platform}/{name}/complete"

    async def _resolve_response(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        match response.status:
            case 200:
                data = await response.json()
                if data.get("error"):
                    raise UnexpectedError()
                return data
            case 400:
                raise BadRequest()
            case 404:
                raise NotFound()
            case 500:
                raise InternalServerError()
            case _:
                raise ServiceUnavailable()

    async def get(self) -> dict[str, Any]:
        url = await self._get_url()
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                try:
                    return await self._resolve_response(r)
                except aiohttp.client_exceptions.ClientPayloadError:
                    raise UnexpectedError()
