import spotipy
import random
import json
import decimal

def get_mood(value):
    if 0.75 <= value <= 1:
        return "happy"
    
    if 0.5 <= value <= 0.749:
        return "meh"
    
    if 0.25 <= value <= 0.49:
        return "sad"

    return "dark"

def populate_cache(sp):
    cache = sp._custom_cache

    top_artists_uri = aggregate_top_artists(sp)
    top_tracks_uri = aggregate_top_tracks(sp, top_artists_uri)

    print("Populating", len(top_tracks_uri), "songs.")
    for tracks in list(top_tracks_uri):
        tracks_all_data = sp.audio_features(tracks)
        track_data = tracks_all_data[0]
        valence = float(format(track_data["valence"], ".2f"))

        track = sp.track(track_data["id"])
        track_name = f'{track["name"]} - {track["artists"][0]["name"]}'

        cache[get_mood(valence)].append((track_data, track_name))
    
    for k,v in cache.items():
        print(k, len(v))
    
    data = json.dumps(cache)

    with open("cache.json", "w") as f:
        f.write(data)


def aggregate_top_artists(sp):
    top_artists_name = []
    top_artists_uri = []
        
    followed_artists_all_data = sp.current_user_followed_artists(limit=50)
    followed_artists_data = followed_artists_all_data["artists"]

    for artist_data in followed_artists_data["items"]:
        if artist_data["name"] not in top_artists_name:
            top_artists_name.append(artist_data["name"])
            top_artists_uri.append(artist_data["uri"])
        
    return top_artists_uri

def aggregate_top_tracks(sp, top_artists_uri):
    top_tracks_uri = []

    for artist in top_artists_uri:
        top_tracks_all_data = sp.artist_top_tracks(artist)
        top_tracks_data = top_tracks_all_data["tracks"]

        for track_data in top_tracks_data:
            top_tracks_uri.append(track_data["uri"])
    
    return top_tracks_uri

def select_tracks(sp, value, limit, search_type):
    cache = sp._custom_cache

    top_artists_uri = aggregate_top_artists(sp)
    top_tracks_uri = aggregate_top_tracks(sp, top_artists_uri)
    selected_tracks_uri = []

    if search_type == "mood":
        for song in [random.choice(cache[get_mood(value)]) for x in range(limit)]:
            selected_tracks_uri.append([song[1], str(song[0]["valence"])])

        if len(selected_tracks_uri) < limit:
            random.shuffle(top_tracks_uri)
        
            for track_data in top_tracks_uri:
                if len(selected_tracks_uri) == limit:
                    break

                track = sp.track(track_data["id"])
                t_name = f'{track["name"]} - {track["artists"][0]["name"]}'

                mood = get_mood(value)
                cache[mood].append((track_data, t_name))
                
                if (value - 0.25) <= track_data["valence"] <= (value + 0.25):
                    selected_tracks_uri.append(t_name, str(track_data["valence"]))

    random.shuffle(top_tracks_uri)
    for tracks in list(top_tracks_uri[0:250]):
        if len(selected_tracks_uri) >= limit:
                break
        
        if cache.get(tracks):
            data = cache.get(tracks)
            track_data = data[0]
            t_name = data[1]

            if (value - 0.25) <= track_data["valence"] <= (value + 0.25):
                selected_tracks_uri.append(t_name, str(track_data["valence"]))
        else:
            tracks_all_data = sp.audio_features(tracks)

            for track_data in tracks_all_data:
                track = sp.track(track_data["id"])
                t_name = f'{track["name"]} - {track["artists"][0]["name"]}'

                cache[tracks] = (track_data, t_name)

                if search_type == "mood":
                    if (value - 0.25) <= track_data["valence"] <= (value + 0.25):
                        selected_tracks_uri.append(t_name, str(track_data["valence"]))
                if search_type == "tempo":
                    if (value - 15) <= track_data["tempo"] <= (value + 15):
                        selected_tracks_uri.append(t_name, str(track_data["valence"]))
    
    return selected_tracks_uri