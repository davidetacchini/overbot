from __future__ import annotations

from typing import Any

import discord

from .profile import Profile
from .paginator import Paginator


class BaseView(discord.ui.View):
    def __init__(
        self, *, interaction: discord.Interaction, timeout: float = 120.0, **kwargs: Any
    ) -> None:
        super().__init__(timeout=timeout, **kwargs)
        self.interaction = interaction
        self.author_id = interaction.user.id
        self.message: None | discord.Message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message(
            "This command was not initiated by you.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        try:
            if self.message:
                await self.message.delete()
            else:
                await self.interaction.delete_original_response()
        except Exception:
            pass


class PromptView(BaseView):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.value: None | bool = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = True
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class SelectPlatform(discord.ui.Select):
    def __init__(self, entries: dict[str, discord.Embed | list[discord.Embed]] = {}) -> None:
        super().__init__(row=0, placeholder="Select a platform...")
        self.entries = entries
        self.add_option(label="PC", value="pc")
        self.add_option(label="Console", value="console")

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        value = self.values[0]
        await self.view.rebind(self.entries[value], interaction)


class SelectProfiles(discord.ui.Select):
    def __init__(self, profiles: list[Profile], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.profiles = profiles
        self.__fill_options()

    def __fill_options(self) -> None:
        for profile in self.profiles:
            self.add_option(label=profile.battletag, value=str(profile.id))


class SelectPlatformMenu(Paginator):
    def __init__(
        self, entries: discord.Embed | list[discord.Embed], interaction: discord.Interaction
    ) -> None:
        super().__init__(entries, interaction=interaction)

    def add_platforms(self, platforms: dict[str, discord.Embed | list[discord.Embed]]) -> None:
        self.clear_items()
        self.add_item(SelectPlatform(entries=platforms))
        self.fill_items(force_quit=True)

    async def rebind(
        self, entries: discord.Embed | list[discord.Embed], interaction: discord.Interaction
    ) -> None:
        if isinstance(entries, discord.Embed):
            entries = [entries]
        self.entries = entries
        self.current = 0
        kwargs = self._get_kwargs_from_page(self.entries[0])
        self._update_labels(0)
        await interaction.response.edit_message(**kwargs, view=self)


class SelectProfileView(BaseView):
    def __init__(self, profiles: list[Profile], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.select = SelectProfiles(profiles, placeholder="Select a profile...")
        setattr(self.select, "callback", self.select_callback)
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class ProfileUnlinkView(BaseView):
    def __init__(self, profiles: list[Profile], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.choices: list[int] = []
        placeholder = "Select at least a profile..."
        # Using min_values=0 to ensure that the view gets recomputed
        # even when the user unselects the previously selected profile(s).
        self.select = SelectProfiles(
            profiles, min_values=0, max_values=len(profiles), placeholder=placeholder
        )
        setattr(self.select, "callback", self.select_callback)
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.choices = list(map(int, self.select.values))

    @discord.ui.button(label="Unlink", style=discord.ButtonStyle.blurple, row=1)
    async def unlink(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.choices:
            await interaction.response.defer()
            await interaction.client.pool.execute(
                "DELETE FROM profile WHERE id = any($1::int[]);", self.choices
            )

            if len(self.choices) == 1:
                message = "Profile successfully unlinked."
            else:
                message = "Profiles successfully unlinked."

            await interaction.delete_original_response()
            await interaction.followup.send(message, ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message(
                "Please select at least a profile to unlink.", ephemeral=True
            )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red, row=1)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class SelectAnswer(discord.ui.Select):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.view.stop()


class HeroInfoView(BaseView):
    def __init__(self, *, interaction: discord.Interaction, data: dict[str, Any]) -> None:
        super().__init__(interaction=interaction)
        self.data = data

    @discord.ui.button(label="Abilities", style=discord.ButtonStyle.blurple)
    async def abilities(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        abilities = self.data.get("abilities")
        if not abilities:
            return

        pages = []
        for index, ability in enumerate(abilities, start=1):
            embed = discord.Embed()
            embed.set_author(name=self.data.get("name"), icon_url=self.data.get("portrait"))
            embed.title = ability.get("name")
            embed.url = ability.get("video").get("link").get("mp4")
            embed.description = ability.get("description")
            embed.set_thumbnail(url=ability.get("icon"))
            embed.set_image(url=ability.get("video").get("thumbnail"))
            embed.set_footer(text=f"Page {index} of {len(abilities)}")
            pages.append(embed)

        await interaction.client.paginate(pages, interaction=interaction)

    @discord.ui.button(label="Story", style=discord.ButtonStyle.blurple)
    async def story(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        story = self.data.get("story")
        if not story:
            return

        chapters = story.get("chapters")
        max_pages = len(chapters) + 1
        pages = []

        embed = discord.Embed()
        embed.set_author(name=self.data.get("name"), icon_url=self.data.get("portrait"))
        embed.url = story.get("media").get("link")
        embed.title = "Origin Story"
        embed.description = story.get("summary")
        embed.set_footer(text=f"Page 1 of {max_pages}")
        pages.append(embed)

        for index, chapter in enumerate(story.get("chapters"), start=2):
            embed = discord.Embed()
            embed.set_author(name=self.data.get("name"), icon_url=self.data.get("portrait"))
            embed.title = chapter.get("title")
            embed.description = chapter.get("content")
            embed.set_image(url=chapter.get("picture"))
            embed.set_footer(text=f"Page {index} of {max_pages}")
            pages.append(embed)

        await interaction.client.paginate(pages, interaction=interaction)

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.red)
    async def quit(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()
