class NoChoice(Exception):
    def __init__(self):
        super().__init__("Took too long.")


class PaginationError(Exception):
    pass


class CannotEmbedLinks(PaginationError):
    def __init__(self):
        super().__init__("Bot cannot embed links in this channel.")
