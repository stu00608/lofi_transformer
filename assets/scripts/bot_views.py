import sys
sys.path.append("..")
import discord
import typing
import pretty_midi
from bot_utils.utils import midi_program_to_emoji


class ModelSelectDropdownView(discord.ui.View):
    def __init__(self, author: typing.Union[discord.Member, discord.User], model_list, model_description_dict, model_emoji_dict):
        super().__init__()
        self.value = None
        self.author = author
        self.add_item(self.make_select_item(model_list, model_description_dict, model_emoji_dict))

    def make_select_item(self, model_list, model_description_dict, model_emoji_dict):
        select = discord.ui.Select(
            placeholder="Select model to generate song.",
            options=[discord.SelectOption(
                label=model,
                value=model,
                emoji=model_emoji_dict[model],
                description=model_description_dict[model],
            ) for model in model_list]
        )
        async def select_callback(interaction):
            await interaction.response.defer()
            self.value = select.values[0]
            self.stop()
        select.callback = select_callback
        return select

class InstrumentSelectDropdownView(discord.ui.View):
    def __init__(self, author: typing.Union[discord.Member, discord.User]):
        super().__init__()
        self.value = None
        self.author = author
    
    # Note: Append instrument program number in `bot_utils.utils`` to extend this select menu. 
    @discord.ui.select(
        placeholder="Select an instrument to render generated midi.",
        options = [discord.SelectOption(
                label=pretty_midi.program_to_instrument_name(program), 
                value=program, emoji=midi_program_to_emoji[program],
                description=f"MIDI Program: {program}") for program in midi_program_to_emoji.keys()]
    )
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        self.value = select.values[0]
        self.stop()

# Define a simple View that gives us a confirmation menu
class Rating(discord.ui.View):
    def __init__(self, author: typing.Union[discord.Member, discord.User]):
        super().__init__()
        self.value = None
        self.author = author
        self.user = None
        self.is_skipped = False
        self.is_rerender = False
        self.is_stopped = False

    async def interaction_check(self, inter: discord.MessageInteraction) -> bool:
        self.user = inter.user
        if inter.user != self.author:
            await inter.response.send_message(content="Warning : You're not the votable user.", ephemeral=True)
            return False
        return True    
    
    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='1', style=discord.ButtonStyle.grey)
    async def one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('You rated 1, thank you!', ephemeral=True)
        self.value = 1
        self.stop()

    @discord.ui.button(label='2', style=discord.ButtonStyle.grey)
    async def two(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('You rated 2, thank you!', ephemeral=True)
        self.value = 2
        self.stop()

    @discord.ui.button(label='3', style=discord.ButtonStyle.grey)
    async def three(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('You rated 3, thank you!', ephemeral=True)
        self.value = 3
        self.stop()

    @discord.ui.button(label='4', style=discord.ButtonStyle.grey)
    async def four(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('You rated 4, thank you!', ephemeral=True)
        self.value = 4
        self.stop()

    @discord.ui.button(label='5', style=discord.ButtonStyle.grey)
    async def five(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('You rated 5, thank you!', ephemeral=True)
        self.value = 5
        self.stop()
        
    @discord.ui.button(label='Skip', style=discord.ButtonStyle.blurple)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Vote skipped.', ephemeral=True)
        self.value = "placeholder"
        self.is_skipped = True
        self.stop()

    @discord.ui.button(label='Re-render', style=discord.ButtonStyle.green)
    async def rerender(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "placeholder"
        self.is_rerender = True
        self.stop()
        
    @discord.ui.button(label='Stop', style=discord.ButtonStyle.red)
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = "placeholder"
        self.is_stopped = True
        self.stop()