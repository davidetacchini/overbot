import aiohttp

import config

from . import exceptions as ex


class Request:

    __slots__ = ("platform", "username", "username_l")

    def __init__(self, platform: str, username: str):
        self.platform = platform
        self.username = username.replace("#", "%23")
        self.username_l: str = username.lower()

    @property
    def account_url(self) -> str:
        return config.overwatch["account"] + "/" + self.username + "/"

    async def resolve_name(self, players: list[dict]) -> None | str:
        if len(players) == 1:
            try:
                return players[0]["urlName"]
            except Exception:
                raise ex.InternalServerError()
        elif len(players) > 1:
            total_players = []
            for player in players:
                if self.platform != "nintendo-switch":
                    name = player["name"].lower()
                else:
                    name = player["urlName"]
                if self.username_l == name and self.platform == player["platform"]:
                    return player["urlName"]
                if self.platform == player["platform"]:
                    total_players.append(name)
            if (
                len(total_players) == 0
                or "#" in self.username
                and self.username_l not in total_players
            ):
                raise ex.NotFound()
            elif len(total_players) == 1 and self.platform == "nintendo-switch":
                return total_players[0]
            else:
                raise ex.TooManyAccounts(self.platform, self.username, len(total_players))
        else:
            # return the username and let `resolve_response` handle it
            return self.username

    async def get_name(self) -> None | list[dict]:
        async with aiohttp.ClientSession() as s:
            async with s.get(self.account_url) as r:
                try:
                    name = await r.json()
                except Exception:
                    raise ex.UnexpectedError()
                else:
                    return await self.resolve_name(name)

    async def url(self) -> str:
        name = await self.get_name()
        return f"{config.base_url}/{self.platform}/{name}/complete"

    async def resolve_response(self, response) -> None | dict:
        match response.status:
            case 200:
                data = await response.json()
                if data.get("error"):
                    raise ex.UnexpectedError()
                return data
            case 400:
                raise ex.BadRequest()
            case 404:
                raise ex.NotFound()
            case 500:
                raise ex.InternalServerError()
            case _:
                raise ex.ServiceUnavailable()

    async def get(self) -> None | dict:
        url = await self.url()
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                try:
                    return await self.resolve_response(r)
                except aiohttp.client_exceptions.ClientPayloadError:
                    raise ex.UnexpectedError()
