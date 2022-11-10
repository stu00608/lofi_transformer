# This example requires the 'members' and 'message_content' privileged intents to function.

import os
import discord
from discord.ext import commands
from time import sleep
import random
import asyncio
import json
from generate import generate_song

token = os.environ["BOT_TOKEN"]

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

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

bot = Bot()

async def load_extensions():
    for f in os.listdir("./cogs"):
	    if f.endswith(".py"):
		    await bot.load_extension("cogs." + f[:-3])

async def main():
    async with bot:
        await load_extensions()
        await bot.start(token)

asyncio.run(main())