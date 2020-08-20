import json
import random

from quart import request, url_for, render_template, redirect, jsonify, abort
from qclass import ClassyBlueprint

from flask_discord import requires_authorization

class Playlists(ClassyBlueprint):
    async def get_quota(self, user_id, *, route="NO_ROUTE"):
        quota = await self.app.db.fetch("SELECT * FROM quota WHERE id=$1", user_id)

        if not quota:
            quota = 10
        else:
            quota = quota[0]["quota"]
        
        return quota

    @requires_authorization
    async def playlists(self, *, route="/"):
        user = self.app.discord.fetch_user()
        pl_list = await self.app.db.fetch("SELECT * FROM playlists WHERE id=$1", user.id)
        quota = await self.get_quota(user.id)

        return await render_template("playlists/my_playlists.html", playlists=pl_list, len=len, user=user, same=True, quota=quota)
    
    @requires_authorization
    async def make_public(self, user_id, key, *, route="/<int:user_id>/<int:key>/public"):
        user = self.app.discord.fetch_user()

        if request.method == "POST":
            if user.id == user_id:
                await self.app.db.execute("UPDATE playlists SET public=true WHERE id=$1 AND key=$2", user_id, key)

                if request.args.get("redirect"):
                    return redirect(request.args.get("redirect"))
    
    async def peek_playlist(self, user_id, key, *, route="/<int:user_id>/<int:key>"):
        user = self.app.discord.fetch_user()
        playlist = await self.app.db.fetch("SELECT * FROM playlists WHERE id=$1 AND key=$2", user_id, key)

        if not playlist:
            return abort(404)
        
        if not playlist[0]["public"]:
            if user.id != playlist[0]["id"]:
                return abort(404)
        
        return await render_template("playlists/playlist.html", user=user, playlist=playlist[0], len=len)
    
    async def search_playlists(self, *, route="/search"):
        user = self.app.discord.fetch_user()

        if request.args.get("query"):
            query = request.args.get("query")
            arg_type = request.args.get("type")
            
            if arg_type == "user":
                playlists = await self.app.db.fetch("SELECT * FROM playlists WHERE username=$1 AND public=true", query)

                if not playlists:
                    return await render_template("playlists/search.html", message=f'Your search for users with the name "{query}" returned no results.')
                
                return await render_template("playlists/search.html", playlists=playlists, user=user, len=len, term=query)
            
            if arg_type == "playlist":
                playlists = await self.app.db.fetch("SELECT * FROM playlists WHERE name=$1 AND public=true", query)

                if not playlists:
                    return await render_template("playlists/search.html", message=f'Your search for playlists containing "{query}" returned no results.', user=user, len=len)
                
                return await render_template("playlists/search.html", playlists=playlists, user=user, len=len, term=query)
            
            if arg_type == "mood":
                mood = self.app.analyze_mood(query)
                playlists = await self.app.db.fetch("SELECT * FROM playlists WHERE public=true")
                returns = []

                for playlist in playlists:
                    value = playlist["mood"]
                    if (value - 0.25) <= mood <= (value + 0.25):
                        returns.append(playlist)

                if not playlists or not returns:
                    return await render_template("playlists/search.html", message=f'Your search for playlists with a mood of "{mood}" returned no results.', user=user, len=len)
                
                return await render_template("playlists/search.html", playlists=returns, user=user, len=len, term=query)
            
            if arg_type == "song" or arg_type == "artist":
                playlists = await self.app.db.fetch("SELECT * FROM playlists WHERE public=true")
                returns = []

                for playlist in playlists:
                    print("iter")
                    for song in playlist["songs"]:
                        if query.lower() in song[0].lower():
                            returns.append(playlist)
                            break

                if not playlists or not returns:
                    return await render_template("playlists/search.html", message=f'Your search for playlists with the {arg_type} "{query}" returned no results.', user=user, len=len, term="")
                
                return await render_template("playlists/search.html", playlists=returns, user=user, len=len, term=query)
        
        playlists = await self.app.db.fetch("SELECT * FROM playlists WHERE public=true")
    
        return await render_template("playlists/search.html", user=user, term=None, len=len, playlist=random.choice(playlists))

    async def user_playlists(self, user_id, *, route="/<int:user_id>"):
        user = self.app.discord.fetch_user()

        if user.id == user_id:
            return redirect("/playlists")

        playlists = await self.app.db.fetch("SELECT * FROM playlists WHERE id=$1 AND public=true", user_id)

        if not playlists:
            return abort(404)

        quota = await self.get_quota(user_id)

        return await render_template("playlists/my_playlists.html", user=user, playlists=playlists, len=len, same=False, quota=quota)
    
    async def remove_song(self, user_id, key, song, *, route="/<int:user_id>/<int:key>/remove/<song>"):
        user = self.app.discord.fetch_user()
        playlist = await self.app.db.fetch("SELECT * FROM playlists WHERE id=$1 AND key=$2", user_id, key)

        if not playlist or playlist[0]["id"] != user_id:
            return redirect("/playlists")
        
        songs = playlist[0]["songs"]
        new_songs = [s for s in songs if s[0] != song]

        await self.app.db.execute("UPDATE playlists SET songs=$1 WHERE id=$2 AND key=$3", new_songs,  user_id, key)

        return redirect(f"/playlists/{user_id}/{key}")

playlists = Playlists("dashboard", __name__, url_prefix="/playlists")