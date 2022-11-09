import sys
sys.path.append("..")
import os
import discord
from time import sleep
from discord.ext import commands
from generate import generate_song

class LofiTransformerPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.getfiles()
        self.lastfile = None

    def getfiles(self):
        filenames = os.listdir("gen")
        filenames = [filename.split(".")[0] for filename in filenames if filename.endswith(".mid")]
        self.filedict = {}
        for filename in filenames:
            mid_path = os.path.join("gen", filename+".mid")
            mp3_path = os.path.join("gen", filename+".mp3")
            self.filedict[filename] = [mid_path, mp3_path]

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def list(self, ctx):
        """List mid and mp3 files in server."""
        self.getfiles()
        keys = self.filedict.keys()
        await ctx.send(keys)
    
    @commands.command()
    async def get(self, ctx, id=None):
        if id is None:
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
            path = generate_song()[0]
            mid_path, mp3_path = path
            self.getfiles()
            self.lastfile = path
        elif id not in self.filedict.keys():
            await ctx.send("Files not found.")
            return
        else:
            song = self.filedict[id]
            mid_path, mp3_path = song

        source = discord.FFmpegPCMAudio(source=mp3_path)
        await ctx.send(f'Now playing: {mp3_path}')
        await ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        while ctx.voice_client.is_playing():
            sleep(.1)
        await ctx.voice_client.disconnect()


    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command()
    async def stop(self, ctx):
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

async def setup(client):
    await client.add_cog(LofiTransformerPlayer(client))