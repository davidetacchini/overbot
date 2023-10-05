from typing import Any

import aiohttp

import config  # pyright: ignore[reportMissingImports]

from .exceptions import (
    BlizzardServerError,
    InternalServerError,
    NotFound,
    TooManyAccounts,
    UnknownError,
    ValidationError,
)


class Request:
    __slots__ = "battletag"

    def __init__(self, battletag: str) -> None:
        self.battletag = battletag

    async def _resolve_name(self, players: list[dict[str, Any]]) -> str:
        if len(players) == 1:
            try:
                return players[0]["battleTag"]
            except Exception:
                raise InternalServerError()
        elif len(players) > 1:
            for player in players:
                if self.battletag.lower() == player["battleTag"].lower():
                    return player["battleTag"]
            raise TooManyAccounts(self.battletag, len(players))
        else:
            # return the battletag and let `resolve_response` handle it
            return self.battletag

    async def _get_name(self) -> str:
        url = config.overwatch["account"] + "/" + self.battletag.replace("#", "%23") + "/"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                try:
                    data = await r.json()
                except Exception:
                    raise UnknownError()
                else:
                    name = await self._resolve_name(data)
                    return name.replace("#", "-")

    async def _resolve_response(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        match response.status:
            case 200:
                return await response.json()
            case 404:
                raise NotFound()
            case 422:
                raise ValidationError()
            case 500:
                raise InternalServerError()
            case 504:
                raise BlizzardServerError()
            case _:
                raise UnknownError()

    async def _request(self, path) -> dict[str, Any]:
        url = config.base_url + path
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                try:
                    return await self._resolve_response(r)
                except aiohttp.client_exceptions.ClientPayloadError:
                    raise UnknownError()

    async def fetch_data(self) -> dict[str, Any]:
        name = await self._get_name()
        return await self._request(f"/players/{name}")

    async def fetch_stats_summary(self) -> dict[str, Any]:
        name = await self._get_name()
        return await self._request(f"/players/{name}/stats/summary")
