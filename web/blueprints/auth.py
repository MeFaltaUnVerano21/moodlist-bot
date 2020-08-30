from quart import request, url_for, render_template, redirect
from qclass import ClassyBlueprint
from flask_discord import requires_authorization

class Auth(ClassyBlueprint):
    async def login(self):
        return self.app.discord.create_session(scope=["identify", "guilds"])

    async def logout(self):
        user = self.app.discord.fetch_user()
        self.app.discord.revoke()

        return redirect(url_for("index"))

    async def callback(self, *, route="login/callback"):
        await self.app.discord.callback()
        user = self.app.discord.fetch_user()

        return redirect(url_for("index"))

auth = Auth("auth", __name__, url_prefix="/")