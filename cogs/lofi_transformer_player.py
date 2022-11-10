import sys
sys.path.append("..")
import os
import json
import discord
from time import sleep
from discord.ext import commands
from generate import generate_song

# Define a simple View that gives us a confirmation menu
class Rating(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

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

def getfiles(out_dir):
    filenames = os.listdir(out_dir)
    filenames = [filename.split(".")[0] for filename in filenames if filename.endswith(".mid")]
    filedict = {}
    for filename in filenames:
        mid_path = os.path.join(out_dir, filename+".mid")
        mp3_path = os.path.join(out_dir, filename+".mp3")
        filedict[filename] = [mid_path, mp3_path]
    return filedict

class LofiTransformerPlayer(commands.Cog):
    def __init__(self, bot, ckpt_path, out_dir):
        self.bot = bot
        self.ckpt_path = ckpt_path
        self.out_dir = out_dir
        self.filedict = getfiles(out_dir)
        self.lastfile = None

        self.song_stats = json.load(open("song_stats.json")) 


    @commands.command()
    async def list(self, ctx):
        """List mid and mp3 files in server."""
        keys = self.filedict.keys()
        await ctx.send(keys)
    
    @commands.command()
    async def get(self, ctx, id=None):
        if id is None:
            if self.lastfile is None:
                await ctx.send("No last file.")
                return
            songs = self.lastfile
        elif id not in self.filedict.keys():
            await ctx.send("Files not found.")
            return
        else:
            songs = self.filedict[id]

        for file in songs:
            await ctx.send(file=discord.File(file))

    @commands.command()
    async def play(self, ctx, id=None):
        """Plays a file from the local filesystem"""

        #TODO: Merge with a get function.
        if id is None:
            await ctx.send(f"Generating...")
            path = generate_song(
                ckpt_path=self.ckpt_path,
                out_dir=self.out_dir
            )[0]
            mid_path, mp3_path = path
            await self.update_dict(ctx)
            self.lastfile = path
        elif id not in self.filedict.keys():
            await ctx.send("Files not found.")
            return
        else:
            song = self.filedict[id]
            mid_path, mp3_path = song
        id = mp3_path.split("/")[-1].split(".")[0]

        source = discord.FFmpegPCMAudio(source=mp3_path)
        embed=discord.Embed(title="Now playing...", description=id, color=0xffc7cd)
        embed.set_thumbnail(url="https://media1.giphy.com/media/mXbQ2IU02cGRhBO2ye/giphy.gif")
        embed.set_footer(text="Please rate the song ⏬")
        rating_view = Rating()
        await ctx.send(embed=embed, view=rating_view)
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

        await rating_view.wait()
        if id not in self.song_stats.keys():
            self.song_stats[id] = {
                "path": mp3_path,
                "view": 1,
                "rate": [rating_view.value]
            }
        else:
            self.song_stats[id]["view"] += 1
            self.song_stats[id]["rate"].append(rating_view.value)
        
        output_json = json.dumps(self.song_stats, indent=4)

        with open("song_stats.json", "w") as j:
            j.write(output_json)
            print("Rate recorded.")

    @commands.command()
    async def leave(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
    
    @list.before_invoke
    @get.before_invoke
    async def update_dict(self, ctx):
        self.filedict = getfiles(self.out_dir)
    


async def setup(client):
    await client.add_cog(LofiTransformerPlayer(
        client,
        ckpt_path="./exp/fourth_finetune_lofi/loss_8_params.pt",
        out_dir="gen/fourth_finetune_lofi"
    ))