import discord
from discord.ext import commands

import wavelink
import asyncio

from typing import Union

from cogs.music import MusicController
from utils.menu import EmbedMenu


DOUBLE_BACK = "\n\n"
SINGLE_BACK = "\n"

class Playlists(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.reactions = [
            "\U0001f604",
            "\U0001f610",
            "\U0001f641",
            "\U0001f62d",
            "\U0001f522",
            "\U000023f9"
        ]

        self.playlist_cache = {}
        self.moods = ["happy", "meh", "sad", "dark"]

        self.music = bot.cogs.get("Music")
    
    def get_controller(self, value: Union[commands.Context, wavelink.Player]):
        if isinstance(value, commands.Context):
            gid = value.guild.id
        else:
            gid = value.guild_id

        try:
            controller = self.music.controllers[gid]
        except KeyError:
            controller = MusicController(self.bot, gid)
            self.music.controllers[gid] = controller

        return controller
    
    async def generate_playlist(self, ctx, value):
        if ctx.command.name == "mood":
            cmd_type = "mood"
        else:
            cmd_type = "tempo"

        new_embed = discord.Embed(colour=self.bot.colour, description="Generating your bespoke playlist  <a:loading:739877158507380846>")
        message = await ctx.send(embed=new_embed)

        amount = await self.bot.get_custom_length(ctx)
        highest = await self.bot.get_length(ctx)

        if not amount:
            amount = highest
        elif amount > highest:
            amount = highest
            await self.bot.delete_limit(ctx)

        async with self.bot.cs.post(f"{self.bot.WEB_URL}/api/generate/{cmd_type}/{value}/{amount}", headers={"x-token": self.bot.http.token}) as r:
            try:
                data = await r.json()
            except Exception:
                return await ctx.send(await r.text())
        
        print(data)
        if len(data["data"]) == 0:
            new_embed.description = "I couldn't find any songs matching your search! Try using a different mood or bpm."
            return await message.edit(embed=new_embed)

        new_embed.description = "Loading songs into the playlist  <a:loading:739877158507380846>"
        await message.edit(embed=new_embed)

        self.playlist_cache[ctx.author.id] = [value, data["data"]]

        controller = self.get_controller(ctx)
        for song in data["data"]:
            query = f'ytsearch:{song[0]} (lyrics video)'

            tracks = await self.bot.wavelink.get_tracks(f'{query}')

            if tracks:
                await controller.queue.put(tracks[0])
        
        new_embed.description = f"Successfully generated a playlist of {len(data['data'])} songs.\n\nWant to generate larger playlists? Consider becoming a patreon [here](https://patreon.com/logan_webb) to increase your playlist sizes, as well as save playlists!"
        await message.edit(embed=new_embed)

        count = await self.bot.db.fetch("SELECT * FROM total")

        if not count:
            return await self.bot.db.execute("INSERT INTO total (total) VALUES (1)")
        
        return await self.bot.db.execute("UPDATE total SET total=$1", count[0]["total"]+1)
    
    @commands.group(name="playlist", aliases=["playlists", "pl"])
    async def playlist_(self, ctx):
        """Playlist parent command, also shows your saved playlists if you are a patreon"""
        if not self.music:
            self.music = self.bot.cogs.get("Music")

        if ctx.subcommand_passed:
            return
        
        length = await self.bot.get_length(ctx)

        if length <= 10:
            return
        
        data = await self.bot.db.fetch("SELECT * FROM playlists WHERE id=$1", ctx.author.id)

        if not data:
            return await ctx.send(embed=discord.Embed(title="Your playlists", description=f"You have no playlists! While the bot is playing, run `m!pl save <PLAYLIST NAME>` to save it!", colour=self.bot.colour))
    
        chunks = self.bot.chunks([pl["name"] for pl in data], 5)
        embeds = []

        for i, lst in enumerate(chunks):
            embed = discord.Embed(title="Your playlists", description=f"Use `m!playlist load <PLAYLIST NAME>` to load a playlist!{DOUBLE_BACK}{SINGLE_BACK.join([f'**{x}**' for x in lst])}", colour=self.bot.colour)
            embed.set_thumbnail(url=self.bot.user.avatar_url_as(format="png"))
            embed.set_footer(text=f"Page {i+1}/{len(list(chunks))}", icon_url=ctx.author.avatar_url_as(format="png"))

            embeds.append(embed)

        menu = EmbedMenu(embeds)
        return await menu.start(ctx)

    @playlist_.command(name="save")
    @commands.is_owner()
    async def save_(self, ctx, *, playlist_name):
        """Save a playlist"""
        await self.bot.db.execute("INSERT INTO playlists (id, name, songs, mood, author, username) VALUES ($1,$2,$3,$4,$5,$6)", ctx.author.id, playlist_name.lower(), self.playlist_cache[ctx.author.id][1], self.playlist_cache[ctx.author.id][0], str(ctx.author), ctx.author.name.lower())

        embed = discord.Embed(colour=self.bot.colour, description=f"Your playlist has been saved under the name **{playlist_name.lower()}**! Use `mood playlist load {playlist_name.lower()}` to load it in the future.")

        return await ctx.send(embed=embed)
    
    @playlist_.command(name="load")
    @commands.is_owner()
    async def load_(self, ctx, *, playlist_name):
        """Load a playlist"""
        if playlist_name.startswith("http://localhost:5000/p"):
            async with self.bot.cs.get(playlist_name.strip(), headers={"x-data-type": "json"}) as r:
                data = [await r.json()]

                if data[0].get("error"):
                    return await ctx.send("Looks like I can't find that playlist!")
        else:
            data = await self.bot.db.fetch("SELECT * FROM playlists WHERE id=$1 AND name=$2", ctx.author.id, playlist_name.lower())

        if not data:
            return await ctx.send("Looks like I can't find that playlist!")
        
        songs = data[0]["songs"]

        player = self.bot.wavelink.get_player(ctx.guild.id)

        if not player.is_connected:
            await ctx.invoke(self.music.connect_)
        
        embed = discord.Embed(colour=self.bot.colour, description="Loading your playlist <a:loading:739877158507380846>")

        status = await ctx.send(embed=embed)
    
        controller = self.get_controller(ctx)
        for song in songs:
            query = f'ytsearch:{song} (lyric video)'

            tracks = await self.bot.wavelink.get_tracks(f'{query}')

            if tracks:
                await controller.queue.put(tracks[0])
        
        embed.description = "Loaded your playlist!"

        return await status.edit(embed=embed)
    
    @playlist_.command(name="bpm")
    async def bpm_(self, ctx, tempo: int):
        """Generate and play a playlist based on a BPM"""
        if not ctx.author.voice:
            return await ctx.send("Please join a voice channel before running this command.")
        
        player = self.bot.wavelink.get_player(ctx.guild.id)

        if not player.is_connected:
            await ctx.invoke(self.music.connect_)

        if ctx.me.voice and ctx.me.voice.channel.id != ctx.author.voice.channel.id:
            return await ctx.send("I am already playing in another channel!")

        return await self.generate_playlist(ctx, tempo)

    @playlist_.command(name="mood")
    async def mood_(self, ctx, mood=None):
        """Testing"""
        try:
            mood = [float(mood)]
        except (ValueError, TypeError):
            mood = await self.bot.analyze_mood(ctx, mood)

        await ctx.send(f"Mood is: {mood[0]}")
    
        if not ctx.author.voice:
            return await ctx.send("Please join a voice channel before running this command.")
        
        player = self.bot.wavelink.get_player(ctx.guild.id)

        if not player.is_connected:
            await ctx.invoke(self.music.connect_)
        
        return await self.generate_playlist(ctx, mood[0])
    
    @playlist_.command(name="limit")
    async def limit_(self, ctx, amount: int):
        """Limit the amount of songs within your playlist generation"""
        highest = await self.bot.get_length(ctx)

        if amount > highest:
            embed = discord.Embed(description=f"The limit you specified is too high! You can only generate playlists with up to **{highest}** songs!\n\nWant to increase your playlist limit? Consider becoming a patreon [here](https://patreon.com/logan_webb)", colour=self.bot.colour)
            
            return await ctx.send(embed=embed)

        exists = await self.bot.db.fetch("SELECT * FROM limits WHERE id=$1", ctx.author.id)

        if not exists:
            query = "INSERT INTO limits (id, custom_limit) VALUES ($1,$2)"
        else:
            query = "UPDATE limits SET custom_limit=$2 WHERE id=$1"
        
        await self.bot.db.execute(query, ctx.author.id, amount)
        
        return await ctx.send("Limit updated")

def setup(bot):
    bot.add_cog(Playlists(bot))