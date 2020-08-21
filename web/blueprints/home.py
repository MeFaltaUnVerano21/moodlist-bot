from quart import render_template, redirect, request, jsonify, abort
from qclass import ClassyBlueprint

from flask_discord import requires_authorization

class Home(ClassyBlueprint):
    async def index(self):
        if self.app.discord.authorized:
            user = self.app.discord.fetch_user()
        else:
            user = None

        fetch = await self.app.db.fetch("SELECT * FROM total")
        playlists = fetch[0]["total"]

        return await render_template("/home/home.html", guilds=self.app.config["guilds"], playlists=playlists, user=user)
    
    @requires_authorization
    async def invite(self):
        user = self.app.discord.fetch_user()
        fetch = await self.app.db.fetch("SELECT * FROM guilds")
        my_guilds = [f["id"] for f in fetch]

        guilds = [g for g in self.app.discord.fetch_guilds() if g.permissions.manage_guild and g.id not in my_guilds]

        return await render_template("home/invite.html", guilds=guilds, my_guilds=my_guilds, str=str, user=user)
    
    async def invite_other(self, guild_id, *, route="/invite/add/<int:guild_id>"):
        url = f"https://discord.com/api/oauth2/authorize?client_id=739489265263837194&permissions=37046592&redirect_uri=http%3A%2F%2Flocalhost%3A5000%2Fdashboard&scope=bot&guild_id={guild_id}"
        return redirect(url)
    
    async def get_playlist(self, key, *, route="/p/<int:key>"):
        headers = request.headers
        playlist = await self.app.db.fetch("SELECT * FROM playlists WHERE key=$1 AND public=true", key)

        if headers.get("x-data-type"):
            data_type = headers.get("x-data-type")

            if data_type == "json":
                if playlist:
                    return jsonify(dict(playlist[0]))
                else:
                    return jsonify({"error": "Playlist not found"}), 404

        user = self.app.discord.fetch_user()

        if not playlist or (playlist[0]["public"] == False and playlist[0]["id"] != user.id) and not request.headers.get("x-data-type"):
            return abort(404)
        
        return redirect(f"/playlists/{playlist[0]['id']}/{key}")

home = Home("home", __name__, url_prefix="/")