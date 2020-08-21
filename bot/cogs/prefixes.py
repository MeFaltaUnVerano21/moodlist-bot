import discord
from discord.ext import commands

class Prefixes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(name="prefix", aliases=["prefixes", "pr"])
    async def prefix_(self, ctx):
        """Prefix command group"""
        if ctx.subcommand_passed:
            return
        
        prefix = ctx.prefix
        embed = discord.Embed(title="Prefix commands", colour=self.bot.colour, description=f"""
**{prefix}prefix show** - Get the current prefix
**{prefix}prefix set** - Set the server prefix (Must have `manage_server` permissions)
**{prefix}prefix reset** - Set the prefix back to the default (`m!`)
        """)

        return await ctx.send(embed=embed)
    
    @prefix_.command(name="show")
    async def prefix_show_(self, ctx):
        """Show the server prefix"""
        prefix = self.bot.prefix_cache.get(ctx.guild.id)

        if not prefix:
            prefix = "m!"
        
        embed = discord.Embed(title=f"Prefix in {ctx.guild}", colour=self.bot.colour, description=f"""
The current prefix is:

**{prefix}**
        """)

        return await ctx.send(embed=embed)
    
    @prefix_.command(name="set", aliases=["update"])
    @commands.has_permissions(manage_guild=True)
    async def prefix_set_(self, ctx, *, prefix):
        """Set the server prefix. Requires the `manage_server` permission."""
        exists = self.bot.prefix_cache.get(ctx.guild.id)

        if not exists:
            query = "INSERT INTO prefixes (id, prefix) VALUES ($1,$2)"
        else:
            query = "UPDATE prefixes SET prefix=$2 WHERE id=$1"
        
        await self.bot.db.execute(query, ctx.guild.id, prefix)
        self.bot.prefix_cache[ctx.guild.id] = prefix

        embed = discord.Embed(title="Prefix set", colour=self.bot.colour, description=f"The server prefix has been set to **{prefix}**")
        return await ctx.send(embed=embed)
    
    @prefix_.command(name="remove", aliases=["reset"])
    @commands.has_permissions(manage_guild=True)
    async def prefix_remove_(self, ctx):
        """Remove the server prefix. Requires the `manage_server` permission."""
        if not self.bot.prefix_cache.get(ctx.guild.id):
            return await ctx.send("This server does not have a custom prefix!")
        
        del self.bot.prefix_cache[ctx.guild.id]
        await self.bot.db.execute("DELETE FROM prefixes WHERE id=$1", ctx.guild.id)

        embed = discord.Embed(title="Prefix removed", colour=self.bot.colour, description=f"The server prefix has been reset, and is now **m!**")
        return await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Prefixes(bot))