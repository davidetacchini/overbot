from utils.i18n import _


class NoChoice(Exception):
    def __init__(self):
        super().__init__(_("Took too long."))
