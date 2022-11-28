import os
import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio

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

        self.initial_extensions = [
            "cogs.lofi_transformer_player"
        ]

        self.day_avatar = "img/day_bocchi.jpg"
        self.night_avatar = "img/night_bocchi.jpg"
        
        self.init_avatar()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
    
    async def setup_hook(self) -> None:
        self.update_avatar.start()
        for ext in self.initial_extensions:
            await self.load_extension(ext)

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

    def init_avatar(self):
        now = datetime.now()
        day_time = datetime.strptime(DAY_TIME, "%H:%M")
        night_time = datetime.strptime(NIGHT_TIME, "%H:%M")
        day_time = now.replace(hour=day_time.hour, minute=day_time.minute)
        night_time = now.replace(hour=night_time.hour, minute=night_time.minute)
        if day_time < now < night_time:
            self.day_night_state = "day"
        else:
            self.day_night_state = "night"

    @tasks.loop(seconds=10)
    async def update_avatar(self):
        if bot.is_closed():
            print("Bot is closed")
            return

        now = datetime.strftime(datetime.now(), '%H:%M')
        if now == DAY_TIME and bot.day_night_state == "night":
            bot.switch_avatar(is_day=True)
        elif now == NIGHT_TIME and bot.day_night_state == "day":
            bot.switch_avatar(is_day=False)

bot = Bot()

@bot.event
async def on_voice_state_update(member, before, after):
    voice_state = member.guild.voice_client
    if voice_state is not None and len(voice_state.channel.members) == 1:
        # If the bot is connected to a channel and the bot is the only one in the channel
        print("Bot getting out.")
        await voice_state.disconnect() # Disconnect the bot from the channel

if __name__ == "__main__":
    bot.run(token)