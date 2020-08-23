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
    
    @commands.command(name="invite", aliases=["invites", "links"])
    async def invite_(self, ctx):
        """Get a list of invites"""
        embed = discord.Embed(title="Useful links", description=f"""
[Invite through our website](https://moodlist.xyz/invite)
[Invite through discord link](https://discord.com/api/oauth2/authorize?client_id=739489265263837194&permissions=37046592&scope=bot)
[Support server](https://discord.gg/kayUTZm)

Consider supporting Moodlist on [patreon](https://patreon.com/logan_webb) in order to receive benefits and keep the bot up and running.
        """, colour=self.bot.colour)
        embed.set_thumbnail(url=self.bot.user.avatar_url_as(format="png"))

        return await ctx.send(embed=embed)
    
    @commands.command(name="tutorial")
    async def tutorial_(self, ctx):
        """Look at the Moodlist Tutorial"""
        embed = await self.bot.load_tutorial(ctx, True)

        return await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Misc(bot))