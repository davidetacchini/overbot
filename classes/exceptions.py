from discord.app_commands import AppCommandError


class NoChoice(Exception):
    def __init__(self) -> None:
        super().__init__("Took too long.")


class PaginationError(Exception):
    pass


class CannotEmbedLinks(PaginationError):
    def __init__(self) -> None:
        super().__init__("Bot cannot embed links in this channel.")


class InvalidColor(AppCommandError):
    def __init__(self) -> None:
        super().__init__(
            "You must enter an hex value (e.g. `#fff`) or an rgb value *comma separated* (e.g. 255, 255, 255)."
        )
