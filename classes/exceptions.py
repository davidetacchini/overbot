class NoChoice(Exception):
    def __init__(self):
        super().__init__("Took too long.")
