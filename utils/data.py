import aiohttp

import config


class RequestError(Exception):
    """Base exception class for data.py."""

    pass


class NotFound(RequestError):
    """Exception raised when a profile is not found."""

    def __init__(self):
        super().__init__(
            "Player not found. Please make sure you aren't missing any capital letter."
        )


class BadRequest(RequestError):
    """Exception raised when a request sucks."""

    def __init__(self):
        super().__init__("Wrong battletag format entered! Correct format: `name#0000`")


class InternalServerError(RequestError):
    """Exception raised when the API returns 500 status code."""

    def __init__(self):
        super().__init__(
            "The API is having internal server problems. Please be patiente and try again later."
        )


class ServiceUnavailable(RequestError):
    """Exception raised when the server API is under maintenance."""

    def __init__(self):
        super().__init__(
            "The API is under maintenance. Please be patiente and try again later."
        )


class Data:
    __slots__ = ("platform", "name")

    def __init__(self, **kwargs):
        self.platform = kwargs.pop("platform", None)
        self.name = kwargs.pop("name", None)

    @property
    def url(self):
        """Returns the resolved url."""
        return f"{config.base_url}/{self.platform}/{self.name}/complete"

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
        async with aiohttp.ClientSession() as s:
            async with s.get(self.url) as r:
                return await self.resolve_response(r)

    async def get(self):
        """Returns resolved response."""
        return await self.response()
