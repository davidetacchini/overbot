import asyncio
from utils.i18n import _

def _fetching_done_callback(fut):
    try:
        fut.exception()
    except (asyncio.CancelledError, Exception):
        pass


class Fetching:
    def __init__(self, ctx):
        self.ctx = ctx

    async def do_fetching(self):
        self._message = await self.ctx.send(_("Fetching..."))

    async def __aenter__(self):
        self.task = asyncio.ensure_future(self.do_fetching())
        self.task.add_done_callback(_fetching_done_callback)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._message.delete()
        self.task.cancel()
