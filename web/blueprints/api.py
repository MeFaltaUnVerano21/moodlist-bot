import spotipy
import json
import os

from quart import request, jsonify
from qclass import ClassyBlueprint
from blueprints.utils import tracks
MOOD_VALUES =  {
    "happy": 1,
    "sad": 0.25,
    "dark": 0,
    "meh": 0.5
}

def load_cache(sp):
    tracks.populate_cache(sp)

class Api(ClassyBlueprint):
    async def check_token(self, headers, *, route="NO_ROUTE"):
        token = headers.get("x-token")

        if not token:
            return ({"error": "Unauthorized, no token provided.", "status": 403}, 403)
        
        valid_token = os.environ.get("API_TOKEN")

        if token != valid_token:
            return ({"error": "Unauthorized, incorrect token given.", "status": 403}, 403)
        
        return [{"message": "Authorized", "status": 200}, 200]

    async def popcache(self):
        auth = await self.check_token(request.headers)

        if auth[0].get("error"):
            return jsonify(auth)

        tracks.populate_cache(self.app.sp)

    async def generate_mood(self, value, amount, *, route="/generate/mood/<value>/<amount>"):
        auth = await self.check_token(request.headers)

        if auth[0].get("error"):
            return jsonify(auth)

        global sp

        mood = MOOD_VALUES.get(value)

        if not mood and mood != 0:
            mood = float(value)

        try:
            selected_tracks_uri = tracks.select_tracks(self.app.sp, mood, int(amount), "mood")
        except spotipy.SpotifyException:
            sp = self.app.refresh()

            selected_tracks_uri = tracks.select_tracks(sp, mood, int(amount), "mood")

        return jsonify({"data": selected_tracks_uri})
    
    async def generate_based_on_song(self, amount, *, route="/generate/song/<int:amount>"):
        auth = await self.check_token(request.headers)

        if auth[0].get("error"):
            return jsonify(auth)
        
        parsed_json = await request.json

        try:
            song = parsed_json["song"].split("-")[1].split("(")[0].strip()
        except IndexError:
            song = parsed_json["song"]

        response = await self.app.cs.get(f"https://api.spotify.com/v1/search/?q={song}&type=track", headers={"Authorization": f"Bearer {self.app.sp.token}"})
        track_data = await response.json()

        try:
            if not track_data["tracks"]["items"]:
                raise KeyError()
        
            audio_features = self.app.sp.audio_features([track_data["tracks"]["items"][0]["uri"]])
            mood = audio_features[0]["valence"]

            try:
                selected_tracks_uri = tracks.select_tracks(self.app.sp, mood, int(amount), "mood")
            except spotipy.SpotifyException:
                sp = self.app.refresh()

                selected_tracks_uri = tracks.select_tracks(sp, mood, int(amount), "mood")
            
            return jsonify({"data": selected_tracks_uri, "mood": mood})
        except KeyError:
            return jsonify({"message": "Track not found", "status": 404}), 404
            

api = Api("api", __name__, url_prefix="/api")