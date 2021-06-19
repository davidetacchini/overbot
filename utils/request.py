import aiohttp

import config

from utils.i18n import _


class RequestError(Exception):

    pass


class NotFound(RequestError):
    def __init__(self):
        super().__init__(_("Player not found."))


class BadRequest(RequestError):
    def __init__(self):
        super().__init__(
            _("Wrong BattleTag format entered! Correct format: `name#0000`")
        )


class InternalServerError(RequestError):
    def __init__(self):
        super().__init__(
            _(
                "The API is having internal server problems. Please be patient and try again later."
            )
        )


class ServiceUnavailable(RequestError):
    def __init__(self):
        super().__init__(
            _("The API is under maintenance. Please be patient and try again later.")
        )


class UnexpectedError(RequestError):
    def __init__(self):
        super().__init__(
            _(
                "Something bad happened during the request. Please be patient and try again."
            )
        )


class TooManyAccounts(RequestError):
    def __init__(self, platform, username, players):
        message = _(
            "**{players}** accounts found under the name of `{username}`"
            " playing on `{platform}`. Please be more specific."
        ).format(players=players, username=username, platform=platform)
        super().__init__(message)


class Request:

    __slots__ = ("platform", "username")

    def __init__(self, *, platform: str, username: str):
        self.platform = platform
        self.username = username

    @property
    def account_url(self):
        return config.overwatch["account"] + "/" + self.username + "/"

    async def resolve_name(self, players):
        if len(players) == 1:
            return players[0]["urlName"]
        elif len(players) > 1:
            total_players = []
            for player in players:
                if (
                    player["name"].lower() == self.username.lower()
                    and player["platform"] == self.platform
                ):
                    return player["urlName"]
                if player["platform"] == self.platform:
                    total_players.append(player["name"].lower())
            if (
                len(total_players) == 0
                or "#" in self.username
                and self.username.lower() not in total_players
            ):
                raise NotFound()
            else:
                raise TooManyAccounts(self.platform, self.username, len(total_players))
        else:
            # return the username and let `resolve_response` handle it
            return self.username

    async def get_name(self):
        async with aiohttp.ClientSession() as s:
            async with s.get(self.account_url) as r:
                try:
                    name = await r.json()
                except aiohttp.ContentTypeError:
                    raise UnexpectedError()
                else:
                    return await self.resolve_name(name)

    async def url(self):
        name = await self.get_name()
        return f"{config.base_url}/{self.platform}/{name}/complete"

    async def resolve_response(self, response):
        if response.status == 200:
            return await response.json()
        elif response.status == 400:
            raise BadRequest()
        elif response.status == 404:
            raise NotFound()
        elif response.status == 500:
            raise InternalServerError()
        else:
            raise ServiceUnavailable()

    async def request(self):
        url = await self.url()
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                try:
                    return await self.resolve_response(r)
                except aiohttp.client_exceptions.ClientPayloadError:
                    raise UnexpectedError()

    async def get(self):
        return await self.request()
