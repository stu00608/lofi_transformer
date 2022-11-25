import sys
sys.path.append("..")
import os
import json
import discord
import typing
import datetime
import numpy as np
from time import sleep
from discord.ext import commands
from generate import generate_song

# Define a simple View that gives us a confirmation menu
class Rating(discord.ui.View):
    def __init__(self, author: typing.Union[discord.Member, discord.User]):
        super().__init__()
        self.value = None
        self.author = author
        self.user = None
        self.is_skipped = False

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
        self.is_skipped = True
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

        ranking = {}
        for key, val in self.song_stats.items():
            # data[key]["score"] = np.sum([item["vote"] for item in val["rate"]])
            vote_list = [item["vote"] for item in val["rate"]]
            score = np.mean(vote_list)
            ranking[key] = score
        ranking = sorted(ranking.items(),key=lambda x:x[1], reverse=True)

        embed=discord.Embed(title="Generated Ranking", description="Find the best one easily")

        if len(ranking) > 9:
            ranking = ranking[:9]
        for id, score in ranking:
            embed.add_field(name=id, value=score)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text="Copy the id and use !play <id> to play the song!")
        
        await ctx.send(embed=embed)
        
    
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

        songs = [discord.File(item) for item in songs]
        await ctx.send(files=songs)

    @commands.command()
    async def play(self, ctx, id=None):
        """Plays a file from the local filesystem"""

        #TODO: Merge with a get function.
        if id is None:
            hint_msg = await ctx.send("Generating...", file=discord.File("img/bocchi.gif"))
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
            hint_msg = await ctx.send(f"Play file...")
            song = self.filedict[id]
            mid_path, mp3_path = song
        id = mp3_path.split("/")[-1].split(".")[0]
        await hint_msg.delete()

        source = discord.FFmpegPCMAudio(source=mp3_path)
        embed=discord.Embed(title="Now playing...", description=id, color=0xffc7cd)
        embed.set_thumbnail(url="https://media1.giphy.com/media/mXbQ2IU02cGRhBO2ye/giphy.gif")
        embed.set_footer(text="Please rate the song ⏬")
        rating_view = Rating(ctx.author)
        vote_area = await ctx.send(embed=embed, view=rating_view)
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

        await rating_view.wait()
        if rating_view.is_skipped:
            await vote_area.delete()
            return

        rate = {"user": rating_view.user.name+"#"+rating_view.user.discriminator, "vote": rating_view.value}
        if id not in self.song_stats.keys():
            self.song_stats[id] = {
                "path": mp3_path,
                "view": 1,
                "rate": [rate],
                "score": None
            }
        else:
            self.song_stats[id]["view"] += 1
            self.song_stats[id]["rate"].append(rate)
        
        output_json = json.dumps(self.song_stats, indent=4)

        with open("song_stats.json", "w") as j:
            j.write(output_json)
            print("Rate recorded.")
        
        await vote_area.edit(embed=embed, view=None)
        # await ctx.send(f"{rating_view.user} has voted!")

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
