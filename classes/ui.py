import discord

from discord import ui

from utils import emojis

PLATFORMS = [
    discord.SelectOption(label="PC", value="pc", emoji=emojis.battlenet),
    discord.SelectOption(label="Playstation", value="psn", emoji=emojis.psn),
    discord.SelectOption(label="XBOX", value="xbl", emoji=emojis.xbl),
    discord.SelectOption(label="Nintendo Switch", value="nintendo-switch", emoji=emojis.switch),
]


class ModalProfileLink(ui.Modal, title="Profile Link"):
    platform = ui.Select(placeholder="Select a platform", options=PLATFORMS)
    username = ui.TextInput(
        label="Username",
        style=discord.TextStyle.short,
        placeholder="Enter your username",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.platform == "pc":
            self.username = self.username.replace("-", "#")

        query = "INSERT INTO profile (platform, username, member_id) VALUES ($1, $2, $3);"
        await interaction.client.pool.execute(
            query, self.platform, self.username, interaction.user.id
        )
        await interaction.followup.send("Profile successfully linked.", ephemeral=True)


class ModalProfileUpdate(ui.Modal, title="Profile Update"):
    platform = ui.Select(placeholder="Select a platform", options=PLATFORMS)
    username = ui.TextInput(
        label="Username",
        style=discord.TextStyle.short,
        placeholder="Enter your username",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.platform == "pc":
            self.username = self.username.replace("-", "#")

        query = "UPDATE profile SET platform = $1, username = $2 WHERE id = $3;"
        await interaction.client.pool.execute(
            query, self.platform, self.username, interaction.user.id
        )
        await interaction.followup.send("Profile successfully updated.", ephemeral=True)


class PromptView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__()
        self.author_id = author_id
        self.value = None

    async def interaction_check(self, interaction):
        if interaction.user and interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("This prompt is not for you.", ephemeral=True)
        return False

    async def on_timeout(self):
        if self.message:
            await self.message.delete()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()
