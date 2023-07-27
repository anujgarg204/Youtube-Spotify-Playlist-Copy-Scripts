# Constants and helpers

SPOTIFY_CLIENT_ID = "your-spotify-client-id"
SPOTIFY_CLIENT_SECRET = "your-spotify-client-secret"
SPOTIFY_REDIRECT_URI = "your-spotify-redirect-uri"
SOURCE_PLAYLIST_ID = "your-source-playlist-id"

YOUTUBE_CLIENT_ID = "your-youtube-client-id"
YOUTUBE_CLIENT_SECRET = "your-youtube-client-secret"
YOUTUBE_API_KEY = "your-youtube-api-key"
YOUTUBE_PLAYLIST_ID = "your-youtube-playlist-id"

def count_elements(arr):
    element_count = {}
    for element in arr:
        if element in element_count:
            element_count[element] += 1
        else:
            element_count[element] = 1
    return element_count

def total_count(arr):
    element_count = count_elements(arr)
    total = 0
    for count in element_count.values():
        total += count
    return total

