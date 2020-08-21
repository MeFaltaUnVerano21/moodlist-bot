import discord
from discord.ext import commands

class NewHelpCommand(commands.MinimalHelpCommand):
    def get_command_signature(self, command):
        return f"{self.clean_prefix}{command.qualified_name} {command.signature}"

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self._original_help = bot.help_command
        bot.help_command = NewHelpCommand()
        bot.help_command.cog = self
    
    def cog_unload(self):
        self.bot.help_command =self._original_help
    
    @commands.command(name="whatsmymood")
    async def whatsmymood_(self, ctx):
        """Analyse your last few messages to determine your mood"""
        data = []

        async for message in ctx.channel.history(limit=100):
            if message.author.id == ctx.author.id:
                data.append(message.content)

        result = await self.bot.analyze_mood(ctx, " ".join(data))
        mood = ""
        if result[0] >= 0.6:
            mood = "happy"
        elif result[0] <= 0.4:
            mood = "sad"
        else:
            mood = "neutral"

        embed = discord.Embed(title="Your overall mood", description=f"After analyzing the last 100 messages within this channel, here is what I found:\n\nYour overall mood on a scale of 0 to 1 is: **{result[0]}**\nYour overall mood is: **{mood.title()}**", colour=self.bot.colour)
        embed.set_thumbnail(url=result[1])

        return await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Misc(bot))