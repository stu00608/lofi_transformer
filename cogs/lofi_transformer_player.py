import sys
sys.path.append("..")
import os
import json
import pretty_midi
import discord
import datetime
import numpy as np
from discord.ext import commands
from generate import generate_song, render_midi
from bot_utils.utils import get_audio_time, getfiles, get_instrument_emoji
from assets.scripts.bot_views import Rating, InstrumentSelectDropdownView, ModelSelectDropdownView

CONFIG_PATH = "./config/config.json"


class LofiTransformerPlayer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.load_config()
        self.select_model(self.config["current_model"])
        self.lastfile = None

    def select_model(self, model):
        self.config["current_model"] = model
        self.save_config()
        self.current_model = model
        self.current_model_ckpt = self.config["model_selection"][self.current_model]["ckpt_path"]
        self.out_dir = self.config["model_selection"][self.current_model]["gen_dir"]
        self.filedict = getfiles(self.out_dir)

        self.load_stats()
    
    def load_stats(self):
        assert (self.config != None) and (self.current_model != None)
        stats_path = os.path.join(
                self.config["model_selection"][self.current_model]["gen_dir"], 
                self.config["model_selection"][self.current_model]["statistic_json_name"]
        )
        if(not os.path.exists(stats_path)):
            self.song_stats = {}
        else:
            self.song_stats = json.load(open(stats_path))
    
    def save_stats(self):
        assert (self.config != None) and (self.current_model != None)
        stats_path = os.path.join(
                self.config["model_selection"][self.current_model]["gen_dir"], 
                self.config["model_selection"][self.current_model]["statistic_json_name"]
        )
        stats = json.dumps(self.song_stats, indent=4)
        with open(stats_path, "w") as j:
            j.write(stats)
    
    def load_config(self):
        self.config = json.load(open(CONFIG_PATH))

    def save_config(self):
        config = json.dumps(self.config, indent=4)
        with open(CONFIG_PATH, "w") as j:
            j.write(config)
        
    @commands.command()
    async def model(self, ctx):
        """Show a dropdown selection to set the model to generate song."""
        current_model = self.config["current_model"]
        current_model_emoji = self.config["model_selection"][current_model]["emoji"]
        model_list = self.config["model_selection"].keys()
        model_description_dict = {m: self.config["model_selection"][m]["description"] for m in model_list}
        model_emoji_dict = {m: self.config["model_selection"][m]["emoji"] for m in model_list}

        view = ModelSelectDropdownView(ctx.author, model_list, model_description_dict, model_emoji_dict)
        await ctx.send(f"Model Setting.\nCurrent model is {current_model_emoji} **{current_model}**", view=view)

        await view.wait()
        self.select_model(view.value)

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

        embed=discord.Embed(title="model", description=self.current_model)
        embed.set_author(name="Generated Song Ranking")

        if len(ranking) > 9:
            ranking = ranking[:9]
        for id, score in ranking:
            embed.add_field(name=id, value=score)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text="Copy the id and use \"!play <id>\" to play the song!")
        
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
            instrument = self.config["instrument"]
            hint_msg = await ctx.send("Generating...", file=discord.File("img/bocchi.gif"))
            path = generate_song(
                instrument=int(instrument),
                ckpt_path=self.current_model_ckpt,
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
        await hint_msg.delete()
        await self.play_command(ctx, mp3_path)

    @commands.command()
    async def leave(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()
    
    @commands.command()
    async def instrument(self, ctx):
        """Show a dropdown selection to set the MIDI render instrument program number."""
        current_instrument = self.config["instrument"]
        emoji = get_instrument_emoji(current_instrument)
        view = self.get_instrument_dropdown_view(ctx)
        await ctx.send(f"Instrument Setting.\nCurrent instrument is {emoji} **{pretty_midi.program_to_instrument_name(current_instrument)}**", view=view)

        await view.wait()
        self.config["instrument"] = int(view.value)
        self.save_config()

    
    async def play_music(self, ctx, id, mp3_path, instrument):
        current_model_emoji = self.config["model_selection"][self.current_model]["emoji"]
        source = discord.FFmpegPCMAudio(source=mp3_path)
        vote_embed=discord.Embed(title=f"Now playing... {get_instrument_emoji(instrument)}", color=0xffc7cd)
        vote_embed.set_thumbnail(url="https://media1.giphy.com/media/mXbQ2IU02cGRhBO2ye/giphy.gif")
        vote_embed.add_field(name="id", value=id, inline=False)
        vote_embed.add_field(name="time", value=get_audio_time(mp3_path), inline=False)
        vote_embed.add_field(name="instrument", value=pretty_midi.program_to_instrument_name(instrument), inline=False)
        vote_embed.add_field(name="model", value=f"{current_model_emoji} {self.current_model}", inline=False)
        vote_embed.set_footer(text="Please rate the song ⏬")
        vote_embed.timestamp = datetime.datetime.now()
        rating_view = Rating(ctx.author)
        vote_area = await ctx.send(embed=vote_embed, view=rating_view)
        ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        return vote_area, vote_embed, rating_view
    
    async def play_command(self, ctx, mp3_path):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        id = mp3_path.split("/")[-1].split(".")[0]
        code, instrument = id.split("_")
        instrument = int(instrument)
        vote_area, embed, rating_view = await self.play_music(ctx, id, mp3_path, instrument)
        await rating_view.wait()
        if rating_view.is_skipped:
            await vote_area.edit(embed=embed, view=None)
            return
        elif rating_view.is_rerender:
            view = self.get_instrument_dropdown_view(ctx)
            await vote_area.edit(embed=embed, view=view)

            await view.wait()
            instrument = int(view.value)
            complete_id = code+"_"+str(instrument)
            print(complete_id)
            if complete_id not in self.filedict.keys():
                # Need to render new one.
                hint_msg = await ctx.send(f"Rendering file to {get_instrument_emoji(int(instrument))}...")
                path = render_midi(
                    instrument=int(instrument),
                    out_dir=self.out_dir,
                    filename=code
                )
                mid_path, mp3_path = path
                await self.update_dict(ctx)
                self.lastfile = path
                id = complete_id
            else:
                hint_msg = await ctx.send(f"Play file...")
                song = self.filedict[complete_id]
                mid_path, mp3_path = song
                id = complete_id
            
            await hint_msg.delete()

            await self.play_command(ctx, mp3_path)
            return

        rate = {"user": rating_view.user.name+"#"+rating_view.user.discriminator, "vote": rating_view.value}

        if id not in self.song_stats.keys():
            self.song_stats[id] = {
                "code": code,
                "time": get_audio_time(mp3_path),
                "instrument": int(instrument),
                "model": self.current_model,
                "path": mp3_path,
                "view": 1,
                "rate": [rate],
                "score": None
            }
        else:
            self.song_stats[id]["view"] += 1
            self.song_stats[id]["rate"].append(rate)
        
        self.save_stats()
        
        await vote_area.edit(embed=embed, view=None)

    def get_instrument_dropdown_view(self, ctx):
        return InstrumentSelectDropdownView(ctx.author)

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
    await client.add_cog(LofiTransformerPlayer(client))
