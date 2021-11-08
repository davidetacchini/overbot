import aiohttp

import config


class RequestError(Exception):

    pass


class NotFound(RequestError):
    def __init__(self):
        super().__init__("Player not found.")


class BadRequest(RequestError):
    def __init__(self):
        super().__init__("Wrong BattleTag format entered! Correct format: `name#0000`")


class InternalServerError(RequestError):
    def __init__(self):
        super().__init__(
            "The API is having internal server problems. Please be patient and try again later."
        )


class ServiceUnavailable(RequestError):
    def __init__(self):
        super().__init__("The API is under maintenance. Please be patient and try again later.")


class UnexpectedError(RequestError):
    def __init__(self):
        super().__init__(
            "Something bad happened during the request. Please be patient and try again."
        )


class TooManyAccounts(RequestError):
    def __init__(self, platform, username, players):
        match platform:
            case "pc":
                what = "BattleTag"
            case "nintendo-switch":
                what = "Nintendo Network ID"
        message = (
            f"**{players}** accounts found under the name of `{username}`"
            f" playing on `{platform}`. Please be more specific by entering"
            f" your full {what}."
        )
        super().__init__(message)


class Request:

    __slots__ = ("platform", "username", "username_l")

    def __init__(self, platform: str, username: str):
        self.platform = platform
        self.username = username
        self.username_l = username.lower()

    @property
    def account_url(self):
        return config.overwatch["account"] + "/" + self.username + "/"

    async def resolve_name(self, players):
        if len(players) == 1:
            return players[0]["urlName"]
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
                raise NotFound()
            elif len(total_players) == 1 and self.platform == "nintendo-switch":
                return total_players[0]
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
