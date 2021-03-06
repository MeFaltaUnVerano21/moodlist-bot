import quart.flask_patch

from quart import Quart, jsonify, request, session

import jwt
import flask_discord as discord
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

from threading import Timer
import aiohttp

import spotipy
import asyncpg
import asyncio

from textblob import TextBlob

import json
import os

from ipc import server

client_id = os.environ.get("SP_CLIENT_ID")
client_secret = os.environ.get("SP_CLIENT_SECRET")
redirect_uri = "http://localhost:8888/callback"
scope = "user-library-read user-top-read playlist-modify-public user-follow-read user-follow-modify"

sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope=scope, show_dialog=True, cache_path="test")

auth_url = sp_oauth.get_authorize_url()
print(auth_url)
response = input('Paste the above link into your browser, then paste the redirect url here: ')

code = sp_oauth.parse_response_code(response)
token_info = sp_oauth.get_access_token(code)

token = token_info['access_token']

sp = spotipy.Spotify(auth=token)
sp._custom_cache = {
    "happy": [],
    "meh": [],
    "sad": [],
    "dark": []
}
sp.token = token

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def refresh():
    global token_info, sp

    token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    token = token_info['access_token']

    _sp = spotipy.Spotify(auth=token)
    _sp._custom_cache = sp._custom_cache
    _sp.token = token

    return _sp

loop = asyncio.get_event_loop()

app = Quart(__name__)
app.loop = loop

ws = server.WsServer(app)

@ws.route
async def now_playing(json):
    return json

app.sp = sp
sp.app = app
app.secret_key = b"flask_key"

app.refresh = refresh

app.config["guilds"] = 0
app.config["SECRET_KEY"] = app.secret_key
app.config["DISCORD_CLIENT_ID"] = "739489265263837194"
app.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.environ.get("MOODLIST_REDIRECT")
app.config["URL"] = os.environ.get("MOODLIST_URL")

class DiscordSubclass(DiscordOAuth2Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @staticmethod
    def __save_state(state):
        session["DISCORD_OAUTH2_STATE"] = state

    @staticmethod
    def __get_state():
        return session.pop("DISCORD_OAUTH2_STATE", str())

    async def callback(self):
        values = await request.values
        error = values.get("error")
        if error:
            if error == "access_denied":
                raise discord.exceptions.AccessDenied()
            raise discord.exceptions.HttpException(error)

        state = self.__get_state()
        token = super()._fetch_token(state)
        self.save_authorization_token(token)

        return jwt.decode(state, app.config["SECRET_KEY"])

app.discord = DiscordSubclass(app)

MOOD_VALUES =  {
    "happy": 1,
    "sad": 0.25,
    "dark": 0,
    "meh": 0.5
}

def analyze_mood(content):
    text = TextBlob(content.lower())

    if text.sentiment.polarity == 0:
        result = 0
    else:
        result = (text.sentiment.polarity + 1) / 2
    
    return result

app.analyze_mood = analyze_mood

import blueprints

blueprints.home.home.register(app)
blueprints.playlists.playlists.register(app)
blueprints.auth.auth.register(app)
blueprints.api.api.register(app)
blueprints.errors.errors.register_errors(app)

with open("cache.json", "r") as f:
    data = json.loads(f.read())

    if not data:
        Timer(2, blueprints.api.load_cache, args=[sp]).start()
    else:
        print(f.read())
        app.sp._custom_cache = data
        
        for k,v in app.sp._custom_cache.items():
            print(k, len(v))

@app.before_first_request
async def before():
    app.db = await asyncpg.create_pool(database="moodlist", user=os.environ.get("PG_NAME"), password=os.environ.get("PG_PASSWORD"))
    app.cs = aiohttp.ClientSession()

    await ws.start()    

if __name__ == "__main__":
    app.run(loop=loop, debug=False, use_reloader=True)