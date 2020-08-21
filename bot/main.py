import discord
from discord.ext import commands

import traceback
import os

import asyncpg
import aiohttp

from textblob import TextBlob

class Bot(commands.Bot):
    def __init__(self):
        self.WEB_URL = "http://localhost:5000"

        super().__init__(command_prefix="m!", case_insensitive=True)

        self.colour = discord.Colour(value=0x80d0c7)

        self.db = None
        self.cs = None

        self.tiers = {
            "royal supporter": 100,
            "gold supporter": 30,
            "silver supporter": 20,
            "bonze supporter": 15
        }

        self.images = {
            "happy": "https://cdn.discordapp.com/attachments/737672423310229524/743108668270182430/moodlist.png",
            "neutral": "https://cdn.discordapp.com/attachments/737672423310229524/743108420101734450/neutral.png",
            "sad": "https://cdn.discordapp.com/attachments/737672423310229524/743108431719956591/sad.png"
        }
    
    # EVENTS
    async def on_connect(self):
        self.load_extension("jishaku")
        for cog in os.listdir("cogs"):
            if cog.startswith("__") or not cog.endswith(".py"):
                continue

            try:
                self.load_extension("cogs." + cog.replace(".py", ""))
                print(cog)
            except Exception:
                traceback.print_exc()
    
    async def on_ready(self):
        print("Ready")

        self.db = await asyncpg.create_pool(database="moodlist", user=os.environ.get("PG_NAME"), password=os.environ.get("PG_PASSWORD"))
        self.cs = aiohttp.ClientSession()

        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="unique playlists | Moodlist"))

        await self.cs.post(f"{self.WEB_URL}/api/updateguilds", json={"guilds": len(self.guilds)})
    
    async def on_guild_join(self, guild):
        await self.cs.post(f"{self.WEB_URL}/api/updateguilds", json={"guilds": len(self.guilds)})
        await self.db.execute("INSERT INTO guilds (id) VALUES ($1)", guild.id)
    
    async def on_guild_remove(self, guild):
        await self.cs.post(f"{self.WEB_URL}/api/updateguilds", json={"guilds": len(self.guilds)})
        await self.db.execute("DELETE FROM guilds WHERE id=$1", guild.id)
    
    # CUSTOM STUFF
    async def get_length(self, ctx):
        member = self.get_guild(605754700503187466).get_member(ctx.author.id)

        if not member:
            return 10

        roles = [r.name.lower() for r in member.roles]

        try:
            limit = max([v for k,v in self.tiers.items() if k in roles])
        except ValueError:
            limit = 10
        
        return limit
    
    async def get_custom_length(self, ctx):
        data = await self.db.fetch("SELECT * FROM limits WHERE id=$1", ctx.author.id)

        if not data:
            return None
        
        return data[0]["custom_limit"]
    
    async def delete_limit(self, ctx):
        return await self.db.execute("DELETE FROM limits WHERE id=$1", ctx.author.id)
    
    def get_image(self, mood):
        img = ""

        if mood >= 0.6:
            img = "happy"
        elif mood <= 0.4:
            img = "sad"
        else:
            img = "neutral"
        
        return self.images[img]

    async def analyze_mood(self, ctx, content=None):
        if content:
            text = TextBlob(content.lower())

            if text.sentiment.polarity == 0:
                result = 0
            else:
                result = (text.sentiment.polarity + 1) / 2
    
            return (result, self.get_image(result))

        data = []

        async for message in ctx.channel.history(limit=100):
            if message.author.id == ctx.author.id:
                data.append(message.content)

        result = await self.analyze_mood(ctx, " ".join(data))

        return result
    
    async def update_quota(self, ctx):
        quota = await self.get_length(ctx)

        await self.db.execute("DELETE FROM quota WHERE id=$1", ctx.author.id)
        await self.db.execute("INSERT INTO quota (id, quota) VALUES ($1,$2)", ctx.author.id, quota)

        return quota

    def chunks(self, data, amount):
        for i in range(0, len(data), amount):
            yield data[i:i + amount]

if __name__ == "__main__":
    Bot().run("NzM5NDg5MjY1MjYzODM3MTk0.XybNCw.MCOjGsQGtu_d--pOQoULiM8no7A")