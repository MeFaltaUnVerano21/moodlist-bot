import discord
from discord.ext import menus

class EmbedMenu(menus.Menu):
    def __init__(self, embeds, dm=False):
        super().__init__(delete_message_after=True)
        
        self.dm = dm
        
        self.pages = embeds
        self.page = 0

    async def send_initial_message(self, ctx, channel):
        if not self.dm:
            return await self.ctx.send(embed=self.pages[0])

        return await self.ctx.author.send(embed=self.pages[0])
    

    @menus.button("\U000025c0")
    async def on_arrow_backward(self, payload):
        if payload.member:
            try:
                await self.message.remove_reaction("\U000025c0", payload.member)
            except discord.Forbidden:
                pass
        else:
            return
        
        if self.page - 1 < 0:
            return
        
        self.page -= 1
        
        return await self.message.edit(embed=self.pages[self.page])
    
    @menus.button("\U000025b6")
    async def on_arrow_forward(self, payload):
        if payload.member:
            try:
                await self.message.remove_reaction("\U000025b6", payload.member)
            except discord.Forbidden:
                pass
        else:
            return
        
        if self.page + 1 > len(self.pages):
            return
        
        self.page += 1
        
        return await self.message.edit(embed=self.pages[self.page])

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f')
    async def on_stop(self, payload):
        await self.ctx.message.add_reaction("\U00002705")
        self.stop()
    
    async def start(self, *args, **kwargs):
        await super().start(*args, **kwargs)
        
        if len(self.pages) == 1:
            await self.message.remove_reaction("\U000025c0", self.ctx.me)
            await self.message.remove_reaction("\U000025b6", self.ctx.me)