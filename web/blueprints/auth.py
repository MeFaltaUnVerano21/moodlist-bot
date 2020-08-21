from quart import request, url_for, render_template, redirect
from qclass import ClassyBlueprint
from flask_discord import requires_authorization

class Auth(ClassyBlueprint):
    async def login(self):
        return self.app.discord.create_session(scope=["identify", "guilds"])

    async def logout(self):
        user = self.app.discord.fetch_user()
        await self.app.cs.post("https://discordapp.com/api/webhooks/746351770170556457/OSdolCDIAF8khHzGxcv23z42f67U2uxngTs0ynf8fw6EzPk9O61lLYLJl-hO4_p9AcBT", json={"content": f"{user} has logged out"})

        self.app.discord.revoke()
        return redirect(url_for("index"))

    async def callback(self, *, route="login/callback"):
        await self.app.discord.callback()

        user = self.app.discord.fetch_user()
        await self.app.cs.post("https://discordapp.com/api/webhooks/746351770170556457/OSdolCDIAF8khHzGxcv23z42f67U2uxngTs0ynf8fw6EzPk9O61lLYLJl-hO4_p9AcBT", json={"content": f"{user} has logged in"})
        return redirect(url_for("index"))

auth = Auth("auth", __name__, url_prefix="/")