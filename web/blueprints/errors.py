import random

from quart import render_template, redirect, url_for
from qclass import ClassyBlueprint

from flask_discord import Unauthorized

MESSAGES = [
    ["It seems you have lost your way, chosen one.", "Walk back home"],
    ["Houston, we have a problem.", "Return to base"],
    ["Be here, you should not.", "Return to base, you must"]
]

class Errors:
    def __init__(self):
        self.app = None

    def register_errors(self, app):
        self.app = app
        app.register_error_handler(404, self.page_not_found)
        app.register_error_handler(Unauthorized, self.discord_unauth)

    async def page_not_found(self, e):
        choice = random.choice(MESSAGES)

        if self.app.discord.authorized:
            user = self.app.discord.fetch_user()
        else:
            user = None

        return await render_template("errors/404.html", message=choice[0], text=choice[1], user=user)

    async def discord_unauth(self, e):
        return redirect(url_for("login"))

errors = Errors()