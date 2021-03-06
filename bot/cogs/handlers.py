import traceback
import sys

import discord
from discord.ext import commands

class Handlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.ignored = ()
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, self.ignored):
            return

        if isinstance(error, self.bot.FirstTimeUse):
            await self.bot.db.execute("INSERT INTO people (id) VALUES ($1)", ctx.author.id)
            self.bot.tutorial_cache.append(ctx.author.id)
            embed = await self.bot.load_tutorial(ctx, False)

            return await ctx.send(embed=embed)

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        
        embed = discord.Embed(title="Oops! Something went wrong!", description=f"**{error}**\n\nJoin the moodlist support server [here](https://discord.gg/kayUTZm) for further support.", colour=self.bot.colour)
        embed.set_thumbnail(url=self.bot.images["sad"])

        return await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Handlers(bot))