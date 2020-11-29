import aiohttp

import config


class RequestError(Exception):
    """Base exception class for data.py."""

    pass


class NotFound(RequestError):
    """Exception raised when a profile is not found."""

    def __init__(self):
        super().__init__("Player not found.")


class BadRequest(RequestError):
    """Exception raised when a request sucks."""

    def __init__(self):
        super().__init__("Wrong battletag format entered! Correct format: `name#0000`")


class InternalServerError(RequestError):
    """Exception raised when the API returns 500 status code."""

    def __init__(self):
        super().__init__(
            "The API is having internal server problems. Please be patient and try again later."
        )


class ServiceUnavailable(RequestError):
    """Exception raised when the server API is under maintenance."""

    def __init__(self):
        super().__init__(
            "The API is under maintenance. Please be patient and try again later."
        )


class TooManyAccounts(RequestError):
    """Exception raise when the API found too many accounts under that name."""

    def __init__(self, platform, name, names):
        if platform == "pc":
            message = (
                f"**{len(names)}** accounts found under the name of `{name}`"
                f" playing on `{platform}`. Please be more specific by entering"
                f" your full battletag in the following format: `name#0000`"
            )
        else:
            message = (
                f"**{len(names)}** accounts found under the name of `{name}`"
                f" playing on `{platform}`. Please be more specific."
            )
        super().__init__(message)


class Data:
    __slots__ = ("platform", "name")

    def __init__(self, **kwargs):
        self.platform = kwargs.get("platform", None)
        self.name = kwargs.get("name", None)

    @property
    def account_url(self):
        return f"{config.overwatch['account']}/{self.name}"

    async def resolve_name(self, names):
        if len(names) == 1:
            return names[0]["urlName"]
        elif len(names) > 1:
            total_names = []
            for name in names:
                if (
                    name["name"].lower() == self.name.lower()
                    and name["platform"] == self.platform
                ):
                    return name["urlName"]
                if name["platform"] == self.platform:
                    total_names.append(name["name"].lower())
            if (
                len(total_names) == 0
                or "#" in self.name
                and self.name.lower() not in total_names
            ):
                raise NotFound()
            else:
                raise TooManyAccounts(self.platform, self.name, total_names)
        else:
            # return self.name and let resolve_response handle it
            return self.name

    async def get_name(self):
        async with aiohttp.ClientSession() as s:
            async with s.get(self.account_url) as r:
                name = await r.json()
                return await self.resolve_name(name)

    async def url(self):
        """Returns the resolved url."""
        name = await self.get_name()
        return f"{config.base_url}/{self.platform}/{name}/complete"

    async def resolve_response(self, response):
        """Resolve the response."""
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

    async def response(self):
        """Returns the aiohttp response."""
        url = await self.url()
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                return await self.resolve_response(r)

    async def get(self):
        """Returns resolved response."""
        return await self.response()
