import quart.flask_patch

from quart import Quart, jsonify, request
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

from threading import Timer
import aiohttp

import spotipy
import asyncpg

from textblob import TextBlob

import json
import os

GA_TRACKING_ID = os.environ.get("GA_TRACKING_ID")

client_id = "00070e6d6685407ea4a370c43fc3d1d8"
client_secret = "766692a177f541bb8291e9316ae7542d"
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

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def refresh():
    global token_info, sp

    token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
    token = token_info['access_token']

    _sp = spotipy.Spotify(auth=token)
    _sp._custom_cache = sp._custom_cache

    return _sp

async def track_event(app, category, action, label=None, value=0):
    data = {
        "v": "1",
        "tid": GA_TRACKING_ID,
        "cid": "555",
        "t": "event",
        "ec": category,
        "ea": action,
        "el": label,
        "ev": value,
        "ua": "Opera/9.80 (Windows NT 6.0) Presto/2.12.388 Verion/12.14"
    }
    response = await app.cs.post("https://www.google-analytics.com/collect", json=data)

    return await response.text()

app = Quart(__name__)
app.track_event = track_event

app.sp = sp
sp.app = app
app.secret_key = b"flask_key"

app.refresh = refresh

app.config["guilds"] = 0
app.config["SECRET_KEY"] = b"jklskfjnakdj"
app.config["DISCORD_CLIENT_ID"] = "739489265263837194"
app.config["DISCORD_CLIENT_SECRET"] = "lL6oIxaMyg4M7ws6nicodQkAb1R-hxHr"
app.config["DISCORD_REDIRECT_URI"] = os.environ.get("MOODLIST_REDIRECT")

app.discord = DiscordOAuth2Session(app)

MOOD_VALUES =  {
    "happy": 1,
    "sad": 0.25,
    "dark": 0,
    "meh": 0.5
}

@app.route("/lol", methods=["POST"])
def get_pl():
    data = request.json
    count = 0

    for uri in data["data"]:
        pl = sp.playlist(uri)
        ids = []

        for track in pl["tracks"]["items"]:
            for artist in track["track"]["artists"]:
                ids.append(artist["id"])

        for data in chunks(ids, 10):
            sp.user_follow_artists(ids=data)
            count += 1
    
    return jsonify({"followed": count})

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

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)