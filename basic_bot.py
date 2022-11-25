# This example requires the 'members' and 'message_content' privileged intents to function.

import os
import discord
from discord.ext import commands, tasks
from time import sleep
from datetime import datetime
import asyncio
from generate import generate_song

token = os.environ["BOT_TOKEN"]

DAY_TIME = "06:00"
NIGHT_TIME = "18:00"


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        description = "Naichen bot."

        super().__init__(
            command_prefix=commands.when_mentioned_or('!'), 
            intents=intents,
            description=description
        )

        self.day_avatar = "day_bocchi.jpg"
        self.night_avatar = "night_bocchi.jpg"
        
        self.update_avatar()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    def switch_avatar(self, is_day: True):
        if is_day:
            with open(self.day_avatar, 'rb') as image:
                asyncio.get_event_loop().create_task(self.user.edit(avatar=image.read()))
                # await self.user.edit(avatar=image.read())
                print("Good morning!")
                self.day_night_state = "day"
        else:
            with open(self.night_avatar, 'rb') as image:
                asyncio.get_event_loop().create_task(self.user.edit(avatar=image.read()))
                # await self.user.edit(avatar=image.read())
                print("Good evening!")
                self.day_night_state = "night"

    def update_avatar(self):
        now = datetime.now()
        day_time = datetime.strptime(DAY_TIME, "%H:%M")
        night_time = datetime.strptime(NIGHT_TIME, "%H:%M")
        day_time = now.replace(hour=day_time.hour, minute=day_time.minute)
        night_time = now.replace(hour=night_time.hour, minute=night_time.minute)
        if day_time < now < night_time:
            self.day_night_state = "day"
        else:
            self.day_night_state = "night"

bot = Bot()


@bot.event
async def on_voice_state_update(member, before, after):
    voice_state = member.guild.voice_client
    if voice_state is not None and len(voice_state.channel.members) == 1:
        # If the bot is connected to a channel and the bot is the only one in the channel
        print("Bot getting out.")
        await voice_state.disconnect() # Disconnect the bot from the channel

@tasks.loop(seconds=10)
async def avatar_update():
    if bot.is_closed():
        print("Bot is closed")
        return

    now = datetime.strftime(datetime.now(), '%H:%M')
    if now == DAY_TIME and bot.day_night_state == "night":
        bot.switch_avatar(is_day=True)
    elif now == NIGHT_TIME and bot.day_night_state == "day":
        bot.switch_avatar(is_day=False)
    
async def load_extensions():
    for f in os.listdir("./cogs"):
	    if f.endswith(".py"):
		    await bot.load_extension("cogs." + f[:-3])

async def main():
    async with bot:
        avatar_update.start()
        await load_extensions()
        await bot.start(token)

asyncio.run(main())