import discord

from utils import emojis
from utils.funcs import get_platform_emoji

from .context import Context
from .exceptions import NoChoice, CannotEmbedLinks

PageT = str | dict | discord.Embed


class Paginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed | str], *, ctx: "Context", **kwargs):
        super().__init__(timeout=120.0, **kwargs)
        if not isinstance(pages, list):
            pages = [pages]

        self.pages = pages
        self.ctx = ctx
        self.current: int = 0
        self.message: discord.Message = None
        self.clear_items()
        self.fill_items()

    @property
    def total(self) -> int:
        return len(self.pages) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            try:
                await self.message.edit(view=None)
            except Exception:
                pass

    def fill_items(self) -> None:
        if self.total > 2:
            self.add_item(self.first)
        if self.total > 0:
            self.add_item(self.previous)
            self.add_item(self.stop_session)
            self.add_item(self.next)
        if self.total > 2:
            self.add_item(self.last)

    def _update_labels(self, page: PageT) -> None:
        self.first.disabled = 0 <= page <= 1
        self.previous.disabled = page == 0
        self.next.disabled = page == self.total
        self.last.disabled = self.total - 1 <= page <= self.total

    def _get_kwargs_from_page(self, page: PageT) -> dict:
        if isinstance(page, dict):
            return page
        elif isinstance(page, discord.Embed):
            return {"content": None, "embed": page}
        elif isinstance(page, str):
            return {"content": page, "embed": None}
        else:
            return {}

    async def _update(self, interaction: discord.Interaction) -> None:
        kwargs = self._get_kwargs_from_page(self.pages[self.current])
        self._update_labels(self.current)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _ensure_permissions(self):
        permissions = self.ctx.channel.permissions_for(self.ctx.me)
        if not permissions.send_messages:
            return
        if not permissions.embed_links:
            raise CannotEmbedLinks

    async def start(self) -> None:
        self._ensure_permissions()
        kwargs = self._get_kwargs_from_page(self.pages[0])
        self._update_labels(0)
        self.message = await self.ctx.send(**kwargs, view=self)

    @discord.ui.button(label="<<", style=discord.ButtonStyle.blurple)
    async def first(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.current > 0:
            self.current = 0
            await self._update(interaction)

    @discord.ui.button(label="<", style=discord.ButtonStyle.blurple)
    async def previous(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.current - 1 >= 0:
            self.current -= 1
            await self._update(interaction)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def stop_session(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label=">", style=discord.ButtonStyle.blurple)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.current + 1 <= self.total:
            self.current += 1
            await self._update(interaction)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.blurple)
    async def last(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        if self.current < self.total:
            self.current = self.total
            await self._update(interaction)


class ProfileManagerView(Paginator):
    def __init__(self, pages, **kwargs):
        super().__init__(pages, **kwargs)
        self.action = None

    def fill_items(self) -> None:
        self.add_item(self.link)
        self.add_item(self.unlink)
        self.add_item(self.update)
        if self.total == 0:
            self.stop_session.row = 1
            self.add_item(self.stop_session)
        super().fill_items()

    async def _handle(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Link", style=discord.ButtonStyle.blurple, row=1)
    async def link(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.action = "link"
        await self._handle(interaction)

    @discord.ui.button(label="Unlink", style=discord.ButtonStyle.blurple, row=1)
    async def unlink(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.action = "unlink"
        await self._handle(interaction)

    @discord.ui.button(label="Update", style=discord.ButtonStyle.blurple, row=1)
    async def update(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        self.action = "update"
        await self._handle(interaction)


class ChooseSelect(discord.ui.Select):
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.handle(interaction, self.values[0])


class ChooseView(discord.ui.View):
    def __init__(
        self,
        entries: None | list[str] = None,
        *,
        ctx: "Context",
        timeout: float = 120.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.entries = entries
        self.ctx = ctx
        self.choice: None | str = None
        self.message: None | discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.delete()

    async def handle(self, interaction: discord.Interaction, selected: str) -> None:
        self.choice = selected
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


async def choose_profile(ctx: "Context", message: str, member: discord.Member = None) -> str:
    view = ChooseView(ctx=ctx)
    select = ChooseSelect(placeholder="Select a profile...")
    view.add_item(select)

    profiles = await ctx.bot.get_cog("Profile").get_profiles(ctx, member)

    for profile in profiles:
        id_, platform, username = profile
        emoji = get_platform_emoji(platform)
        select.add_option(label=f"{username}", value=id_, emoji=emoji)

    view.message = await ctx.send(message, view=view)
    await view.wait()

    if (choice := view.choice) is not None:
        return await ctx.bot.get_cog("Profile").get_profile(choice)
    raise NoChoice()


async def choose_answer(
    entries: list[str | discord.Embed],
    *,
    ctx: "Context",
    timeout: float,
    embed: discord.Embed,
) -> str:
    view = ChooseView(entries, ctx=ctx, timeout=timeout)
    select = ChooseSelect(placeholder="Select the correct answer...")
    view.add_item(select)

    embed.description = ""
    for index, entry in enumerate(entries, start=1):
        select.add_option(label=entry)
        embed.description = f"{embed.description}{index}. {entry}\n"

    view.message = await ctx.send(embed=embed, view=view)
    await view.wait()

    if (choice := view.choice) is not None:
        return choice
    raise NoChoice()


async def choose_platform(ctx: "Context") -> str:
    options = [
        discord.SelectOption(label="PC", value="pc", emoji=emojis.battlenet),
        discord.SelectOption(label="Playstation", value="psn", emoji=emojis.psn),
        discord.SelectOption(label="XBOX", value="xbl", emoji=emojis.xbl),
        discord.SelectOption(label="Nintendo Switch", value="nintendo-switch", emoji=emojis.switch),
    ]

    view = ChooseView(ctx=ctx)
    select = ChooseSelect(placeholder="Select a platform...")
    view.add_item(select)

    for option in options:
        select.append_option(option)

    view.message = await ctx.send("Select a platform...", view=view)
    await view.wait()

    if (choice := view.choice) is not None:
        return choice
    raise NoChoice()
