import requests
from bs4 import BeautifulSoup
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import common
import os
import googleapiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow

# YouTube API credentials
youtube_client_id = common.YOUTUBE_CLIENT_ID
youtube_client_secret = common.YOUTUBE_CLIENT_SECRET
youtube_api_key = common.YOUTUBE_API_KEY

# Spotify API credentials
spotify_client_id = common.SPOTIFY_CLIENT_ID
spotify_client_secret = common.SPOTIFY_CLIENT_SECRET
spotify_redirect_uri = common.SPOTIFY_REDIRECT_URI  # Set this in the Spotify Developer Dashboard

# OAuth 2.0 scopes required for accessing the user's liked videos and creating a playlist
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/youtube.force-ssl"]

# Perform OAuth 2.0 authentication
flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", scopes=SCOPES)
credentials = flow.run_local_server(port=0)

# Authenticate with YouTube API
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=youtube_api_key)

# Authenticate with Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_client_id,
                                               client_secret=spotify_client_secret,
                                               redirect_uri=spotify_redirect_uri,
                                               scope="playlist-modify-private"))

# Fetch YouTube playlist items using playlist id
def get_youtube_playlist_items(youtube_playlist_id):
    youtube_playlist_items = youtube.playlistItems().list(
    part="snippet",
    playlistId=youtube_playlist_id,
    maxResults=10  # Adjust as per your requirement
    ).execute()
    return youtube_playlist_items

# Create new Youtube playlist
def create_new_youtube_playlist(title, description):
    request = youtube.playlists().insert(
        part="snippet",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "privacyStatus": "private"  # You can change the privacy status if needed (private, public, unlisted)
            }
        }
    )

    response = request.execute()

    return response["id"]

#Get Youtube playlist Id with the title
def get_youtube_playlist_id_by_title(playlist_title):
    request = youtube.playlists().list(
        part="snippet",
        mine=True,
        maxResults=50  # Maximum number of results per page
    )

    response = request.execute()

    for item in response.get("items", []):
        if item["snippet"]["title"] == playlist_title:
            return item["id"]

    return None

# Create a new Spotify playlist
def create_new_spotify_playlist(playlist_name, playlist_description):
    spotify_playlist = sp.user_playlist_create(sp.current_user()["id"], name=playlist_name, public=False, description=playlist_description)
    return spotify_playlist

# Add songs to the new Spotify playlist
def copy_yt_playlist_to_spotify_using_api(youtube_playlist_items, spotify_playlist):
    for item in youtube_playlist_items["items"]:
        video_id = item["snippet"]["resourceId"]["videoId"]
        request = youtube.videos().list(
            part="snippet",
            id=video_id
        )

        response = request.execute()

        if response.get("items"):
            video_info = response["items"][0]["snippet"]
            track_title = video_info["title"]
            artist =  video_info["channelTitle"]
            if not track_title or not artist:
                print(f"Nothing found about the video_id: '{video_id}' on youtube")
            else:
                results = sp.search(q=f"{track_title} {artist}", type="track", limit=1)
                if results and "tracks" in results and "items" in results["tracks"] and len(results["tracks"]["items"]) > 0:
                    # Add the first search result to the playlist
                    track_uri = results["tracks"]["items"][0]["uri"]
                    sp.playlist_add_items(playlist_id=spotify_playlist["id"], items=[track_uri])


def copy_yt_playlist_to_spotify_using_scraping(spotify_playlist_id, youtube_video_ids):
    def scrape_youtube_video_title(video_id):
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        # Send a GET request to the YouTube video URL
        response = requests.get(youtube_url)

        # Parse the HTML content of the webpage using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")
        # Find the video title element in the HTML
        title_element = soup.find("meta", property="og:title")

        if title_element and "content" in title_element.attrs:
            video_title = title_element["content"]
            return video_title
        else:
            return None
        
    def search_track_on_spotify_and_add_to_playlist(playlist_id, track_title):
        def search_track(title):
            results = sp.search(q=title, type="track", limit=1)
            if results["tracks"]["items"]:
                result = results["tracks"]["items"][0]["uri"]
                print(f"Found track: '{result}' ")
                return result
            return None

        playlist_tracks = set(item["track"]["uri"] for item in sp.playlist_items(playlist_id)["items"])

        # Search for tracks on Spotify using track titles and add them to the playlist
        track_uri = search_track(track_title)
        if track_uri and track_uri not in playlist_tracks:
            sp.playlist_add_items(playlist_id, [track_uri])

    for video_id in youtube_video_ids:
        video_title = scrape_youtube_video_title(video_id)
        if video_title is not None:
            search_track_on_spotify_and_add_to_playlist(spotify_playlist_id, video_title)
            # This prevents your IP from getting blocked by Youtube Rate Limiter
            time.sleep(1.5)

# Get liked videos from Youtube. Returns a list of video ids.
def fetch_liked_youtube_video_ids(youtube):
    liked_videos = []
    nextPageToken = None

    while True:
        request = youtube.videos().list(
            part="snippet",
            myRating="like",
            maxResults=5000,  # Maximum number of results per page
            pageToken=nextPageToken
        )

        response = request.execute()

        for item in response.get("items", []):
            liked_videos.append(item["id"])

        nextPageToken = response.get("nextPageToken")
        if not nextPageToken:
            break

    return liked_videos

# Add videos to Youtube playlist
def add_videos_to_youtube_playlist(playlist_id, video_ids):
    for video_id in video_ids:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            }
        )

        request.execute()

# Remove duplicates from a Spotify playlist
def remove_duplicates_from_spotify_playlist(playlist_id):
    # Get the current track URIs in the playlist
    playlist_tracks = [item["track"]["uri"] for item in sp.playlist_items(playlist_id)["items"]]

    # Find and remove duplicates
    unique_track_uris = []
    for track_uri in playlist_tracks:
        if track_uri not in unique_track_uris:
            unique_track_uris.append(track_uri)

    # Clear the current playlist
    sp.playlist_replace_items(playlist_id, [])
    # Add the unique tracks back to the playlist
    sp.playlist_add_items(playlist_id, unique_track_uris)

# Get all spotify playlist tracks
def get_all_spotify_playlist_tracks(playlist_id):
    all_tracks = []
    results = sp.playlist_tracks(playlist_id, fields="items(track(name,uri)),next")
    all_tracks.extend(results['items'])

    while results['next']:
        results = sp.next(results)
        all_tracks.extend(results['items'])

    return all_tracks 


# Example usage:
if __name__ == "__main__":
    # Your code here. Basically you just have to call the functions with parameters of your choice. 

    # remove_duplicates_from_playlist(spotify_client_id, spotify_client_secret, spotify_redirect_uri, playlist_id)
    
    # Sample usage
    yt_playlist_id = get_youtube_playlist_id_by_title('Playlist 1')
    print(yt_playlist_id)