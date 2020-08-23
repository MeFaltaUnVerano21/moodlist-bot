import asyncio

import datetime
import humanize
import itertools

import re
import sys
import traceback
import math

import wavelink

import discord
from discord.ext import commands

from typing import Union

RURL = re.compile('https?:\/\/(?:www\.)?.+')

class MusicController:

    def __init__(self, bot, guild_id):
        self.bot = bot
        self.guild_id = guild_id
        self.channel = None

        self.next = asyncio.Event()
        self.queue = asyncio.Queue()

        self.volume = 40
        self.now_playing = None

        self.bot.loop.create_task(self.controller_loop())

    async def controller_loop(self):
        await self.bot.wait_until_ready()

        player = self.bot.wavelink.get_player(self.guild_id)
        await player.set_volume(self.volume)

        while True:
            if self.now_playing:
                await self.now_playing.delete()

            self.next.clear()

            song = await self.queue.get()
            await player.play(song)

            try:
                del self.bot.cogs["Music"].votes[self.guild_id]
            except KeyError:
                pass
            
            embed = discord.Embed(description=f"Now playing: \"{song}\"", colour=self.bot.colour)
            self.now_playing = await self.channel.send(embed=embed)

            voice_channel = self.bot.get_channel(player.channel_id)
            await self.bot.ipc("now_playing", {"guild_id": self.guild_id, "song": str(song), "members": voice_channel.voice_states})

            await self.next.wait()

class Music(commands.Cog):
    """Music controller related commands, for playlist generating look at the playlists category"""

    def __init__(self, bot):
        self.bot = bot
        self.controllers = {}

        self.votes = {}

        self.playlist_cache = {}

        if not hasattr(bot, 'wavelink'):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.start_nodes())

    def get_node_info(self, region):
        config = {
            "host": "167.172.50.54",
            "password": "lavalink@root@logan",
            "identifier": region.upper(),
            "region": region
        }

        if region == "us_central":
            config["port"] = 20000
        else:
            config["port"] = 20001
        config["rest_uri"] = f"http://{config['host']}:{config['port']}"

        return config

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        us_node = await self.bot.wavelink.initiate_node(**self.get_node_info("us_central"))
        eu_node = await self.bot.wavelink.initiate_node(**self.get_node_info("eu_central"))

        us_node.set_hook(self.on_event_hook)
        eu_node.set_hook(self.on_event_hook)
    
    async def on_event_hook(self, event):
        """Node hook callback."""
        if isinstance(event, (wavelink.TrackEnd, wavelink.TrackException)):
            controller = self.get_controller(event.player)
            controller.next.set()

    def get_controller(self, value: Union[commands.Context, wavelink.Player]):
        if isinstance(value, commands.Context):
            gid = value.guild.id
        else:
            gid = value.guild_id

        try:
            controller = self.controllers[gid]
        except KeyError:
            controller = MusicController(self.bot, gid)
            self.controllers[gid] = controller

        return controller

    async def cog_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def cog_command_error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.command(name='connect')
    async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
        """Connect to a valid voice channel."""
        if not channel:
            try:
                channel = ctx.author.voice.channel
            except AttributeError:
                raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

        player = self.bot.wavelink.get_player(ctx.guild.id)
        await ctx.send(f'Connecting to **{channel.name}**')
        await player.connect(channel.id)

        controller = self.get_controller(ctx)
        controller.channel = ctx.channel

    @commands.command(name="play", aliases=["p"])
    async def play_(self, ctx, *, query: str):
        """Search for and add a song to the Queue."""
        if not RURL.match(query):
            query = f'ytsearch:{query} (audio)'

        tracks = await self.bot.wavelink.get_tracks(f'{query}')

        if not tracks:
            return await ctx.send('Could not find any songs with that query.')

        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.is_connected:
            await ctx.invoke(self.connect_)

        track = tracks[0]

        controller = self.get_controller(ctx)
        await controller.queue.put(track)

        embed = discord.Embed(colour=self.bot.colour, description=f"Added **{str(track)}** to the queue.")

        return await ctx.send(embed=embed)

    @commands.command(name="pause")
    async def pause_(self, ctx):
        """Pause the player."""
        player = self.bot.wavelink.get_player(ctx.guild.id)

        if not player.is_playing:
            return await ctx.send('I am not currently playing anything!')

        await player.set_pause(True)

        embed = discord.Embed(colour=self.bot.colour, description="Paused the player, use `mood resume` to resume.")

        return await ctx.send(embed=embed)

    @commands.command(name="resume")
    async def resume_(self, ctx):
        """Resume the player from a paused state."""
        player = self.bot.wavelink.get_player(ctx.guild.id)
        if not player.paused:
            return await ctx.send('I am not currently paused!', )

        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(name="Pausing the player, use `mood pause` to pause.", icon_url=self.bot.user.avatar_url_as(format="png"))

        return await ctx.send(embed=embed)
        await player.set_pause(False)

    @commands.command(name="skip")
    async def skip_(self, ctx):
        """Voteskip a song"""
        player = self.bot.wavelink.get_player(ctx.guild.id)

        if not player.current:
            return await ctx.send("I am not currently playing anything.")

        if not ctx.author.voice:
            return await ctx.send("You aren't in a voice channel.")
        
        return await player.stop()
        if len(ctx.author.voice.channel.members)-1 == 1:
            await player.stop()

            embed = discord.Embed(colour=self.bot.colour)
            embed.set_author(name="Skipped the song!", icon_url=self.bot.user.avatar_url_as(format="png"))

            return await ctx.send(embed=embed)
    
        votes = self.votes.get(ctx.guild.id, None)

        if not votes:
            self.votes[ctx.guild.id] = (1, [])
            new_votes = 1
        else:
            if ctx.author.id in votes[1]:
                return await ctx.send("You have already voted!")
            new_votes = votes[0] + 1
        
        needed = round(math.floor(len(ctx.author.voice.channel.members)-1)*0.75)
        if new_votes >= needed:
            del self.votes[ctx.guild.id]
            await player.stop()
            
            embed = discord.Embed(colour=self.bot.colour)
            embed.set_author(name="Skipped the song!", icon_url=self.bot.user.avatar_url_as(format="png"))

            return await ctx.send(embed=embed)
        else:
            voters = self.votes[ctx.guild.id][1]
            voters.append(ctx.author.id)
            self.votes[ctx.guild.id] = (new_votes, voters)

            embed = discord.Embed(colour=self.bot.colour)
            embed.set_author(name=f"Vote skip - {self.votes[ctx.guild.id][0]}/{needed}", icon_url=self.bot.user.avatar_url_as(format="png"))

            return await ctx.send(embed=embed)


    @commands.command(name="volume", aliases=["vol"])
    async def volume_(self, ctx, *, vol: int=None):
        """Set the player volume."""
        player = self.bot.wavelink.get_player(ctx.guild.id)
        controller = self.get_controller(ctx)

        if not vol:
            embed = discord.Embed(colour=self.bot.colour)
            embed.set_author(name=f"The current volume is {controller.volume}", icon_url=self.bot.user.avatar_url_as(format="png"))

            return await ctx.send(embed=embed)

        vol = max(min(vol, 1000), 0)
        controller.volume = vol

        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(name=f"Setting the player volume to **{vol}**", icon_url=self.bot.user.avatar_url_as(format="png"))

        await player.set_volume(vol)
        return await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=['np', 'current'])
    async def now_playing_(self, ctx):
        """Retrieve the currently playing song."""
        player = self.bot.wavelink.get_player(ctx.guild.id)

        if not player.current:
            embed = discord.Embed(colour=self.bot.colour)
            embed.set_author(name="Nothing is currently playing.", icon_url=self.bot.user.avatar_url_as(format="png"))

            return await ctx.send(embed=embed)

        controller = self.get_controller(ctx)

        try:
            await controller.now_playing.delete()
        except AttributeError:
            pass

        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(name=f"Now playing: {player.current}", icon_url=self.bot.user.avatar_url_as(format="png"))

        controller.now_playing = await ctx.send(embed=embed)

    @commands.command(name="queue", aliases=['q'])
    async def queue_(self, ctx):
        """Retrieve information on the next 5 songs from the queue."""
        player = self.bot.wavelink.get_player(ctx.guild.id)
        controller = self.get_controller(ctx)

        if not player.current or not controller.queue._queue:
            return await ctx.send('There are no songs currently in the queue.')

        upcoming = list(itertools.islice(controller.queue._queue, 0, 5))

        fmt = '\n'.join(f'**`{str(song)}`**' for song in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)} songs out of {len(controller.queue._queue)}', description=fmt, colour=self.bot.colour)
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(format="png"))

        await ctx.send(embed=embed)

    @commands.command(name="stop", aliases=['disconnect', 'dc'])
    async def stop_(self, ctx):
        """Stop and disconnect the player and controller."""
        player = self.bot.wavelink.get_player(ctx.guild.id)

        try:
            del self.controllers[ctx.guild.id]
        except KeyError:
            pass

        await player.disconnect()
        await player.destroy()

        embed = discord.Embed(colour=self.bot.colour)
        embed.set_author(name="Stopped the player.", icon_url=self.bot.user.avatar_url_as(format="png"))

        return await ctx.send(embed=embed)

    @commands.command(name="info")
    @commands.is_owner()
    async def info_(self, ctx):
        """Retrieve various Node/Server/Player information."""
        player = self.bot.wavelink.get_player(ctx.guild.id)
        node = player.node

        used = humanize.naturalsize(node.stats.memory_used)
        total = humanize.naturalsize(node.stats.memory_allocated)
        free = humanize.naturalsize(node.stats.memory_free)
        cpu = node.stats.cpu_cores

        fmt = f'**WaveLink:** `{wavelink.__version__}`\n\n' \
              f'Connected to `{len(self.bot.wavelink.nodes)}` nodes.\n' \
              f'Best available Node `{self.bot.wavelink.get_best_node().__repr__()}`\n' \
              f'`{len(self.bot.wavelink.players)}` players are distributed on nodes.\n' \
              f'`{node.stats.players}` players are distributed on server.\n' \
              f'`{node.stats.playing_players}` players are playing on server.\n\n' \
              f'Server Memory: `{used}/{total}` | `({free} free)`\n' \
              f'Server CPU: `{cpu}`\n\n' \
              f'Server Uptime: `{datetime.timedelta(milliseconds=node.stats.uptime)}`'
        await ctx.send(fmt)


def setup(bot):
    bot.add_cog(Music(bot))