class OverBotException(Exception):
    """Base exception type for OverBot commands."""

    pass


class NoChoice(OverBotException):
    def __init__(self) -> None:
        super().__init__("Took too long.")


class PaginationError(OverBotException):

    pass


class CannotEmbedLinks(PaginationError):
    def __init__(self) -> None:
        super().__init__("Bot cannot embed links in this channel.")


class InvalidColor(OverBotException):
    def __init__(self) -> None:
        super().__init__(
            "You must enter an hex value (e.g. `#fff`) or an rgb value *comma separated* (e.g. 255, 255, 255)."
        )


class CannotCreateGraph(OverBotException):
    def __init__(self) -> None:
        super().__init__("I don't have enough data to create the graph.")


class RequestError(OverBotException):

    pass


class NotFound(RequestError):
    def __init__(self) -> None:
        super().__init__("Profile not found.")


class BadRequest(RequestError):
    def __init__(self) -> None:
        super().__init__("Wrong BattleTag format entered! Correct format: `name#0000`")


class InternalServerError(RequestError):
    def __init__(self) -> None:
        super().__init__(
            "The API is having internal server problems. Please be patient and try again later."
        )


class ServiceUnavailable(RequestError):
    def __init__(self) -> None:
        super().__init__("The API is under maintenance. Please be patient and try again later.")


class UnexpectedError(RequestError):
    def __init__(self) -> None:
        super().__init__("Something bad happened. Please be patient and try again.")


class TooManyAccounts(RequestError):
    def __init__(self, platform: str, username: str, players: int) -> None:
        match platform:
            case "pc":
                what = "BattleTag"
            case "nintendo-switch":
                what = "Nintendo Network ID"
        message = (
            f"**{players}** accounts found named `{username}` playing"
            f" on `{platform}`. Please be more specific by entering"
            f" your full {what}."
        )
        super().__init__(message)


class ProfileException(OverBotException):

    pass


class NoStats(ProfileException):
    def __init__(self) -> None:
        super().__init__("This profile has no quick play nor competitive stats to display.")


class NoHeroStats(ProfileException):
    def __init__(self, hero: str) -> None:
        super().__init__(
            f"This profile has no quick play nor competitive stast for **{hero}** to display."
        )
