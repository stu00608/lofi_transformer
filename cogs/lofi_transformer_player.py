import sys
sys.path.append("..")
import os
import json
import pretty_midi
import discord
import datetime
import logging
import random
import asyncio
import numpy as np
from colorama import Fore, init
from discord.ext import commands
import assets.settings.setting as setting
from generate import generate, render_midi_to_mp3 
from bot_utils.utils import get_audio_time, getfiles, get_instrument_emoji
from assets.scripts.bot_views import Rating, InstrumentSelectDropdownView, ModelSelectDropdownView
init()

CONFIG_PATH = "./config/config.json"

logger = setting.logging.getLogger("lofi_transformer")


class LofiTransformerPlayer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.load_config()
        self.select_model(self.config["current_model"])
        self.lastfile = None

        self.queue = []
        self.keep_looping = False
        logger.info("Lofi Transformer Cog loaded!")

    def select_model(self, model):
        self.config["current_model"] = model
        self.save_config()
        self.current_model = model
        self.current_model_ckpt = self.config["model_selection"][self.current_model]["ckpt_path"]
        self.out_dir = self.config["model_selection"][self.current_model]["gen_dir"]
        self.filedict = getfiles(self.out_dir)

        self.load_stats()
    
    def load_stats(self):
        """Load song stats from current model generation folder."""
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
        """Save song stats to current model generation folder."""
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
    
    @commands.command(name="sync")
    async def _sync(self, ctx):
        await ctx.send(f"Sync commands to current guild.")
        fmt = await ctx.bot.tree.sync()
        await ctx.send(f"Synced {len(fmt)} commands to current guild.")
    
    @commands.hybrid_command(name="pick", description="Pick random song from best samples.")
    async def _pick(self, ctx):
        """Pick randomly from songs that not voted by user in current model."""
        await self.stop_looping()
        self.load_stats()
        pickable_songs = []
        for key, val in self.song_stats.items():
            vote_list = [item["user"] for item in val["rate"]]
            if not str(ctx.author) in vote_list:
                pickable_songs.append(val)
        if pickable_songs == []:
            await ctx.reply(content="You have voted all songs generated by this model.")
        else:
            pick = random.choice(pickable_songs)
            picked_mp3_path = pick["path"]
            picked_mid_path = os.path.join(os.path.dirname(picked_mp3_path), pick["code"], ".mid") # FIXME: Bad approach.
            await self.update_dict(ctx)
            self.lastfile = (picked_mid_path, picked_mp3_path)
            await self.ensure_voice(ctx)
            await self.play_command(ctx, picked_mp3_path)
        
    @commands.hybrid_command(name="model", description="Dropdown menu to set generation model.")
    async def _model(self, ctx):
        """Show a dropdown selection to set the model to generate song."""
        current_model = self.config["current_model"]
        current_model_emoji = self.config["model_selection"][current_model]["emoji"]
        model_list = self.config["model_selection"].keys()
        model_description_dict = {m: self.config["model_selection"][m]["description"] for m in model_list}
        model_emoji_dict = {m: self.config["model_selection"][m]["emoji"] for m in model_list}

        view = ModelSelectDropdownView(ctx.author, model_list, model_description_dict, model_emoji_dict)
        model_select_message = await ctx.send(f"Model Setting.\nCurrent model is {current_model_emoji} **{current_model}**", view=view)

        await view.wait()
        if view.value == None:
            logger.info("Model selection view timeout")
            return
        model_emoji = self.config["model_selection"][view.value]["emoji"]
        await model_select_message.edit(content=f"Model changed to {model_emoji} **{view.value}**", view=None)
        self.select_model(view.value)

    @commands.hybrid_command(name="list", description="List best songs generated in current model.")
    async def _list(self, ctx):
        """List mid and mp3 files in server."""
        self.load_stats()
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
        
    
    # TODO: Fix get command in hybird_command
    @commands.hybrid_command(name="get", description="Give id to get .mid and .mp3 files of the song.")
    async def _get(self, ctx, id: str=None):
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

    @commands.hybrid_command(name="play", description="Generate a song!")
    async def _play(self, ctx, id=None):
        """Plays a file from the local filesystem"""
        state = await self.ensure_voice(ctx)
        if not state:
            logger.debug("User not in a voice channel, quit play command.")
            return
        await self.stop_looping()
        if id is None:
            instrument = self.config["instrument"]
            current_model_emoji = self.config["model_selection"][self.current_model]["emoji"]
            hint_msg = await ctx.send(f"Generating...\nmodel: {current_model_emoji} **{self.current_model}**\ninstrument: {get_instrument_emoji(instrument)} **{pretty_midi.program_to_instrument_name(instrument)}**", file=discord.File("img/bocchi.gif"))
            path = generate(
                ckpt=self.current_model_ckpt,
                out=self.out_dir,
                instrument=int(instrument),
                display=False
            )
            mid_path, mp3_path = path
            await self.update_dict(ctx)
            self.lastfile = path
        elif id not in self.filedict.keys():
            await ctx.send("Files not found.")
            return
        else:
            hint_msg = await ctx.send(f"Play file...")
            path = self.filedict[id]
            mid_path, mp3_path = path
            self.lastfile = path
        await hint_msg.delete()
        await self.play_command(ctx, mp3_path)

    @commands.hybrid_command(name="instrument", description="Dropdown menu to select render instrument.")
    async def _instrument(self, ctx):
        """Show a dropdown selection to set the MIDI render instrument program number."""
        current_instrument = self.config["instrument"]
        emoji = get_instrument_emoji(current_instrument)
        view = self.get_instrument_dropdown_view(ctx)
        instrument_setting_message = await ctx.send(f"Instrument Setting.\nCurrent instrument is {emoji} **{pretty_midi.program_to_instrument_name(current_instrument)}**", view=view)

        await view.wait()
        if view.value == None:
            logger.info("Instrument select view timeout.")
            return
        self.config["instrument"] = int(view.value)
        self.save_config()
        current_instrument = self.config["instrument"]
        emoji = get_instrument_emoji(current_instrument)
        await instrument_setting_message.edit(content=f"Instrument changed to {emoji} **{pretty_midi.program_to_instrument_name(current_instrument)}**", view=None)

    @commands.command()
    async def leave(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()
    
    async def send_rating_view(self, ctx, id, mp3_path, instrument, votable=True):
        # TODO: Should make model as a parameter.
        # TODO: Should be able to reach every needed info from mp3_path
        current_model_emoji = self.config["model_selection"][self.current_model]["emoji"]
        vote_embed=discord.Embed(title=f"Now playing... {get_instrument_emoji(instrument)}", color=0xffc7cd)
        vote_embed.set_thumbnail(url="https://media1.giphy.com/media/mXbQ2IU02cGRhBO2ye/giphy.gif")
        vote_embed.add_field(name="id", value=id, inline=False)
        vote_embed.add_field(name="time", value=get_audio_time(mp3_path), inline=False)
        vote_embed.add_field(name="instrument", value=f"{get_instrument_emoji(instrument)} {pretty_midi.program_to_instrument_name(instrument)}", inline=False)
        vote_embed.add_field(name="model", value=f"{current_model_emoji} {self.current_model}", inline=False)
        vote_embed.set_footer(text="Please rate the song ???")
        vote_embed.timestamp = datetime.datetime.now()
        rating_view = Rating(ctx.author, votable=votable)
        vote_area = await ctx.send(id, embed=vote_embed, view=rating_view)
        return vote_area, vote_embed, rating_view
    
    async def play_music(self, ctx, mp3_path):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        source = discord.FFmpegPCMAudio(source=mp3_path)
        ctx.voice_client.play(source, after=lambda e: logger.error(f'Player error: {e}') if e else None)
    
    async def play_command(self, ctx, mp3_path, play_music=True, votable=True):
        id = mp3_path.split("/")[-1].split(".")[0]
        code, instrument = id.split("_")
        instrument = int(instrument)
        vote_area, embed, rating_view = await self.send_rating_view(ctx, id, mp3_path, instrument, votable)
        if play_music:
            await self.play_music(ctx, mp3_path)
        await rating_view.wait()
        if rating_view.value == None:
            logger.info("Rating view timeout.")
        elif rating_view.is_pick:
            await self._pick(ctx)
        elif rating_view.is_replay:
            await self.ensure_voice(ctx)
            await vote_area.edit(embed=embed, view=None)
            await self.play_command(ctx, mp3_path)
        elif rating_view.is_stopped:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await vote_area.delete()
            await self.play_command(ctx, mp3_path, play_music=False)
        elif rating_view.is_quitted:
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            ctx.voice_client.disconnect()
            await vote_area.edit(embed=embed, view=None)
        elif rating_view.is_skipped:
            await vote_area.edit(embed=embed, view=None)
            await self.ensure_voice(ctx)
            await self._play(ctx)
        elif rating_view.is_rerender:
            view = self.get_instrument_dropdown_view(ctx)
            await vote_area.edit(embed=embed, view=view)

            await view.wait()
            if view.value == None:
                logger.info("Re-render view timeout.")
                return
            await vote_area.edit(embed=embed, view=None)
            instrument = int(view.value)
            complete_id = code+"_"+str(instrument)
            if complete_id not in self.filedict.keys():
                hint_msg = await ctx.send(f"Rendering file to {get_instrument_emoji(instrument)}...")
                path = render_midi_to_mp3(
                    mid_file_path=self.out_dir+code+".mid",
                    out_dir=self.out_dir,
                    instrument=instrument,
                    mp3_file_path=self.out_dir+code+f"_{instrument}"+".mp3"
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
        else:
            if votable:
                # FIXME: Should create the metadata right after generate but not first time vote.
                rate = {"user": rating_view.user.name+"#"+rating_view.user.discriminator, "vote": rating_view.value}
                if id not in self.song_stats.keys():
                    self.song_stats[id] = {
                        "code": code,
                        "time": get_audio_time(mp3_path),
                        "instrument": instrument,
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
            await self.play_command(ctx, mp3_path, play_music=False, votable=False)
    
    @commands.hybrid_command(name="loop", description="Infinitely generate songs and play with current model and instrument setting.")
    async def _loop(self, ctx):
        response = await self.ensure_voice(ctx)
        if not response:
            logger.debug("Quit loop command")
            return
        server = ctx.message.guild
        voice_client = server.voice_client
        if self.keep_looping and (voice_client.is_playing() or voice_client.is_paused()): # NOTE: If keep_looping and playing, prevent task reinvoke.
            logger.debug("Already in loop.")
            return
        
        self.keep_looping = True
        if len(self.queue) == 0:
            await ctx.defer()
            task = asyncio.create_task(self.generate_song(2))
            logger.debug("Waiting first generation task finish.")
            await task
        logger.debug("Started to play loop.")
        await ctx.send("Started to play loop. Call /stop to terminate.")
        loop_task = asyncio.create_task(self.play_loop(ctx))
        await self.generate_song_task(ctx, 3)
    
    @commands.hybrid_command(name="pause", description="Pause the playing audio.")
    async def _pause_media(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("You are not connected to a voice channel.")
            return
        await ctx.defer()
        server = ctx.message.guild
        voice_channel = server.voice_client

        voice_channel.pause()
        await ctx.send("Paused", ephemeral=True)

    @commands.hybrid_command(name="resume", description="Resume the playing audio.")
    async def _resume_media(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("You are not connected to a voice channel.")
            return
        await ctx.defer()
        server = ctx.message.guild
        voice_channel = server.voice_client

        voice_channel.resume()
        await ctx.send("Resumed", ephemeral=True)

    @commands.hybrid_command(name="stop", description="Stop the playing audio.")
    async def _stop_media(self, ctx):
        self.queue = []
        self.keep_looping = False
        if not ctx.message.author.voice:
            await ctx.send("You are not connected to a voice channel.")
            return
        await ctx.defer()
        server = ctx.message.guild
        voice_channel = server.voice_client

        if voice_channel:
            voice_channel.stop()
        await ctx.send("Stopped", ephemeral=True)
    
    async def stop_looping(self):
        if not self.keep_looping:
            return
        self.keep_looping = False
        logger.debug("Wait 2 sec to stop looping")
        await asyncio.sleep(2)

    async def generate_song(self, num_songs=5):
        """Generate the song asynchronously, store path in global queue."""
        while(len(self.queue) < num_songs and self.keep_looping):
            logger.debug("Generating...")
            path = generate(
                ckpt=self.current_model_ckpt,
                out="./loop_file",
                instrument=int(self.config["instrument"]),
                display=False
            )
            logger.debug("Finished!")
            mid_path, mp3_path = path
            self.queue.append(path)

    async def generate_song_task(self, ctx, num_songs=5):
        while self.keep_looping:
            while(len(self.queue) >= num_songs):
                if not self.keep_looping or not ctx.voice_client:
                    logger.debug("Quit from generate_song_task")
                    return
                logger.debug("Queue full now.")
                await asyncio.sleep(3)
            logger.debug("Generating...")
            path = generate(
                ckpt=self.current_model_ckpt,
                out="./loop_file",
                instrument=int(self.config["instrument"]),
                display=False
            )
            logger.debug("Finished!")
            mid_path, mp3_path = path
            self.queue.append(path)

    async def play_loop(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("You are not connected to a voice channel.")
        elif len(self.queue) == 0:
            await ctx.send("Playing queue is empty.")
        else:
            await self.ensure_voice(ctx)
            voice_client = ctx.message.guild.voice_client
            while self.queue and self.keep_looping:
                try:
                    while voice_client.is_playing() or voice_client.is_paused():
                        logger.debug(f"Hi in loop. {self.queue}")
                        await asyncio.sleep(3)
                except AttributeError:
                    logger.error("Attribute error.")
                try:
                    mid_path, mp3_path = self.queue[0]
                    if not os.path.exists(mp3_path):
                        logger.debug("mp3 file not exist, delete and play next.")
                        del(self.queue[0])
                        continue
                    logger.debug(f"Play song: {mp3_path} {get_audio_time(mp3_path)}")
                    source = discord.FFmpegPCMAudio(source=mp3_path)
                    if ctx.voice_client == None:
                        logger.warning(f"{Fore.YELLOW}voice_client == None{Fore.RESET}")
                        break
                    ctx.voice_client.play(source, after=lambda e: logger.error(f'Player error: {e}') if e else None)
                    await asyncio.sleep(2)
                    if os.path.exists(mid_path):
                        os.remove(mid_path)
                    else:
                        logger.warning("mid file not exist.")
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)
                    else:
                        logger.warning("mp3 file not exist.")
                    del(self.queue[0])
                except Exception as e:
                    logger.error(f"{Fore.RED}Got error in play section.{Fore.RESET}\n{e}")
                    break


    def get_instrument_dropdown_view(self, ctx):
        return InstrumentSelectDropdownView(ctx.author)

    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                # raise commands.CommandError("Author not connected to a voice channel.")
                return False
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        return True
    
    @_list.before_invoke
    @_get.before_invoke
    async def update_dict(self, ctx):
        self.filedict = getfiles(self.out_dir)

async def setup(client):
    await client.add_cog(LofiTransformerPlayer(client))
