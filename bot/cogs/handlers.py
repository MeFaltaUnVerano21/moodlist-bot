import traceback
import sys

import discord
from discord.ext import commands

from utils import checks
from utils.menu import TutorialMenu

class Handlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, checks.NotUsedBot):
            # The user hasn't used the bot before.
            menu = TutorialMenu(self.bot.get_tutorial(ctx))
            
            await menu.start(ctx)
            await self.bot.wait_for("on_menu_complete", check=lambda m: m.author.id == ctx.author.id and m.id == ctx.message.id)
            
            await ctx.author.send(f"You have completed the tutorial! If you would like to re-run the tutorial, simply use `{ctx.prefix}tutorial`")
            return await self.bot.db.execute("INSERT INTO people (id, used_bot) VALUES ($1,$2)", ctx.author.id, True)

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        
        return await ctx.send(f"Oops! Something went wrong! **{error}**")

def setup(bot):
    bot.add_cog(Handlers(bot))