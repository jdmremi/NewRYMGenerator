import os
import time
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from bs4 import BeautifulSoup, ResultSet
from difflib import SequenceMatcher
from dotenv import load_dotenv

# Load .env vars
load_dotenv()

# Spotify OAuth manager stuff
CLIENT_ID: str = os.getenv("CLIENT_ID")
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET")
REDIRECT_URI: str = os.getenv("REDIRECT_URI")
SCOPES: str = os.getenv("SCOPES")
USER_ID: str = os.getenv("USER_ID")

class SpotifyAuthManager:
    """
    SpotifyAuthManager is a class that manages authentication and interactions with the Spotify API.
    Methods:
        __init__(client_id: str, client_secret: str, redirect_uri: str, scopes: str, user_id: str):
        create_playlist(title: str, description: str) -> str:
        add_tracks_to_playlist(playlist_id: str, tracks: list) -> None:
        get_tracks_from_album(artist_name: str, title: str, similarity_threshold: float = 0.95) -> list:
        get_track(artist_name: str, title: str, similarity_threshold: float = 0.95) -> str:
        get_n_most_popular_from_album(album_id: str, count: int) -> list:
            Gets the n most popular tracks from an album.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: str, user_id: str):
        """
        Initializes the Spotify client with the provided credentials and settings.

        Args:
            client_id (str): The client ID for the Spotify application.
            client_secret (str): The client secret for the Spotify application.
            redirect_uri (str): The redirect URI for the Spotify application.
            scopes (str): A space-separated list of scopes for the Spotify application.
            user_id (str): The user ID for the Spotify user.

        Attributes:
            spotify (spotipy.Spotify): An instance of the Spotipy Spotify client authenticated with the provided credentials.
        """
        self.spotify: spotipy.Spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scopes,
            )
        )

    def create_playlist(self, title: str, description: str = "Curated by yours truly.") -> str:
        """
        Creates a new playlist on Spotify with the given title and description.

        Args:
            title (str): The title of the playlist.
            description (str): The description of the playlist.

        Returns:
            str: The ID of the created playlist.
        """
        created_playlist = self.spotify.user_playlist_create(
            user=USER_ID, name=title, description=description)
        return created_playlist["id"]

    def add_tracks_to_playlist(self, playlist_id: str, tracks: list) -> None:
        """
        Adds a list of tracks to a specified Spotify playlist.

        Args:
            playlist_id (str): The Spotify ID of the playlist to which tracks will be added.
            tracks (list): A list of track URIs to be added to the playlist.

        Returns:
            None: Returns None.
        """
        # If more than 99 tracks, we need to split it into chunks.
        if len(tracks) >= 99:
            chunks: list[list] = Utils.divide_chunks(tracks)
            for chunk in chunks:
                self.spotify.playlist_add_items(playlist_id, chunk)
        else:
            self.spotify.playlist_add_items(playlist_id, tracks)


    def get_tracks_from_album(self, artist_name: str, title: str, similarity_threshold: float = 0.95) -> list:
        """
        Retrieves the track URIs from an album on Spotify based on the artist name and album title.

        Args:
            artist_name (str): The name of the artist.
            title (str): The title of the album.
            similarity_threshold (float, optional): The threshold for string similarity to match the artist name and album title. Defaults to 0.95.

        Returns:
            list: A list of track URIs from the album if found, otherwise an empty list.
        """
        query: str = f"{artist_name} {title}"
        album_query: dict = self.spotify.search(query, type="album")
        albums: list = album_query["albums"]["items"]

        if not albums:
            return []

        album: dict = albums[0]
        album_id: str = album["uri"]

        if similarity_threshold == 0.0:
            album_tracks_query: dict = self.spotify.album_tracks(album_id=album_id)
            return [track["uri"] for track in album_tracks_query["items"]]

        album_name: str = album["name"]
        artist: str = album["artists"][0]["name"]
        artist_similarity: float = Utils.str_similarity(artist, artist_name)
        title_similarity: float = Utils.str_similarity(title, album_name)

        if artist_similarity >= similarity_threshold and title_similarity >= similarity_threshold:
            as_percentage: float = artist_similarity * 100.0
            ts_percentage: float = title_similarity * 100.0
            print(f"Artist similarity: {as_percentage:.2f}% | Title similarity: {ts_percentage:.2f}%")
            album_tracks_query: dict = self.spotify.album_tracks(album_id=album_id)
            return [track["uri"] for track in album_tracks_query["items"]]

        return []


    def get_track(self, artist_name: str, title: str, similarity_threshold: float = 0.95) -> str:
        """
        Searches for a track on Spotify based on the provided artist name and title.

        Args:
            artist_name (str): The name of the artist.
            title (str): The title of the track.
            similarity_threshold (float, optional): Threshold for string similarity to consider a match. Defaults to 0.95.

        Returns:
            str: The URI of the track if found and matches the similarity threshold, otherwise an empty string.
        """
        # Combine artist name and title for the query.
        query: str = f"{artist_name} {title}"
        track_query: dict = self.spotify.search(query, type="track", limit=2)
        tracks: list = track_query["tracks"]["items"]

        if not tracks:
            return ""

        track: dict = tracks[0]
        if similarity_threshold == 0.0:
            return track["uri"]

        # Check similarity of artist and track names.
        artist: str = track["artists"][0]["name"]
        track_name: str = track["name"]
        artist_similarity: float = Utils.str_similarity(artist, artist_name)
        title_similarity: float = Utils.str_similarity(track_name, title)

        if artist_similarity >= similarity_threshold and title_similarity >= similarity_threshold:
            as_percentage: float = artist_similarity * 100.0
            ts_percentage: float = title_similarity * 100.0
            print(f"Artist similarity: {as_percentage:.2f}% | Title similarity: {ts_percentage:.2f}%")
            return track["uri"]

        return ""
    
    # Gets the n most popular tracks from an album.
    def get_n_most_popular_from_album(self, album_id: str, count: int) -> list:
        pass

class RYMParser:
    """
    A class to parse Rate Your Music (RYM) pages and extract entries.

    Attributes:
        spotify (SpotifyAuthManager): An instance of SpotifyAuthManager for Spotify authentication.
        pages_path (str): The path to the directory containing the pages to be parsed.

    Methods:
        get_entries():
            Lists pages in the specified directory and parses each page to extract entries.

        parse_page(page_path: str) -> list:
            Parses a single page to extract entries and their URLs.
            Args:
                page_path (str): The path to the page to be parsed.
            Returns:
                list: A list of dictionaries containing the title and type (album or track) of each entry.
    """

    def __init__(self, spotify_manager: SpotifyAuthManager, pages_path: str = "./pages/"):
        """
        Initializes the main class with a Spotify authentication manager and a path to pages.

        Args:
            spotify_manager (SpotifyAuthManager): An instance of SpotifyAuthManager for handling Spotify authentication.
            pages_path (str, optional): The file path to the pages directory. Defaults to "./pages/".
        """
        self.pages_path: str = pages_path
        self.spotify = spotify_manager

    def get_entries(self) -> list:
        """
        Retrieves and processes entries from pages located in the specified directory.

        This method performs the following steps:
        1. Lists all files in the directory specified by `self.pages_path`.
        2. Asserts that there is at least one file in the directory.
        3. Iterates over each file, constructs its full path, and processes it using the `parse_page` method.

        Raises:
            AssertionError: If no pages are found in the directory.
        """
        # List pages
        pages: list[str] = os.listdir(self.pages_path)

        # If no pages found, exit.
        assert len(pages) > 0, "No pages found."

        results: list[list] = []

        for page in pages:
            full_path: str = self.pages_path + page
            list_entries: list = self.parse_page(full_path)
            results.extend(list_entries)

        return results

    def parse_page(self, page_path: str) -> list:
        """
        Parses an HTML page to extract music release information.

        Args:
            page_path (str): The file path to the HTML page to be parsed.

        Returns:
            list: A list of dictionaries containing the title and type of each release found on the page.

        Raises:
            AssertionError: If no entries are found on the page.
            AssertionError: If no URLs are found in the entries.
            AssertionError: If entries cannot be simplified.
            AssertionError: If no results are found after processing the URLs.
        """

        results = []

        with open(page_path, "r") as file:
            file_content = file.read()
            soup: BeautifulSoup = BeautifulSoup(file_content, "html.parser")
            list_items: ResultSet[any] = soup.find_all(
                "td", class_="main_entry")

            # If no entries found, exit.
            assert len(list_items) > 0, "No entries found."

            # Get a list of all of the URLs found on the page.
            urls: list[str] = [
                item.find("a", class_="list_album")
                    .get("href")
                for item in list_items
            ]

            # If no URLs found, exit.
            assert len(urls) > 0, "No URLs found!"

            # Gives us "Artist Name Release Name"
            entries_simplified: list[dict] = [
                {
                    "artist": entry.find('a', {'class': 'list_artist'}).text,
                    "title": entry.find('a', {'class': 'list_album'}).text
                }
                for entry in list_items
                if entry is not None
            ]

            assert len(entries_simplified) > 0, "Entries not simplified."

        # If the url contains "/release/single/", then we will search for that song.
        # Otherwise, we will assume it's an album/EP and then search for that album.
        for index, url in enumerate(urls):
            release_type = "track" if "/release/single/" in url else "album"
            results.append({
                "artist": entries_simplified[index]["artist"],
                "title": entries_simplified[index]["title"],
                "type": release_type
            })

        assert len(urls) == len(entries_simplified), "URL list and track info do not match!"
        assert len(results) > 0, "No results found."

        return results

class Utils:
    """
        A utility class providing static methods, such as string similarity comparison and list chunking.

        Methods:
            str_similarity(lhs_title: str, rhs_title: str) -> float:

            divide_chunks(l: list, n: int):
    """
    @staticmethod
    def str_similarity(lhs_title: str, rhs_title: str) -> float:
        """
        Calculate the similarity ratio between two strings using the SequenceMatcher.

        Args:
            lhs_title (str): The first string to compare.
            rhs_title (str): The second string to compare.

        Returns:
            float: A float value between 0 and 1 representing the similarity ratio
                   between the two input strings. A value of 1 indicates identical
                   strings, while 0 indicates completely different strings.
        """
        return SequenceMatcher(None, lhs_title, rhs_title).ratio()

    @staticmethod
    def divide_chunks(l: list, n: int = 99) -> list[list]:
        """
        Splits a list into smaller chunks of a specified size.

        Args:
            l (list): The list to be divided into chunks.
            n (int, optional): The maximum size of each chunk. Defaults to 99.

        Returns:
            list[list]: A list of lists, where each sublist is a chunk of the original list.
        """
        list_splitted = [l[x:x+n] for x in range(0, len(l), n)]
        return list_splitted

if __name__ == "__main__":

    playlist_name: str = ""

    add_to_existing: str = input("Add to existing playlist? (y/n)").lower()

    if add_to_existing == 'y':
        playlist_name: str = input("Please enter the ID of the playlist you wish to add to: ")
    else:
        playlist_name: str = input("Please enter a name for the playlist: ")

    spotify: SpotifyAuthManager = SpotifyAuthManager(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scopes=SCOPES, user_id=USER_ID)
    parser: RYMParser = RYMParser(spotify_manager=spotify)

    # Get entries from downloaded pages.
    list_entries: list = parser.get_entries()
    
    print(f"{len(list_entries)} entries found.")

    # Holds a list of Spotify URIs to be added to playlist.
    to_be_added: list[str] = []

    # Fetch track URIs from Spotify from the information we've gathered from our lists.
    for index, list_entry in enumerate(list_entries):
        artist_name: str = list_entry["artist"]
        title: str = list_entry["title"]
        type: str = list_entry["type"]

        print(f"{index}/{len(list_entries)} {artist_name} - {title}")

        if type == "album":
            album_items: list = spotify.get_tracks_from_album(artist_name=artist_name, title=title)
            to_be_added.extend(album_items)
        else:
            item: str = spotify.get_track(artist_name=artist_name, title=title)
            to_be_added.append(item)

        # So that we don't flood API lmao
        time.sleep(0.25)

    # Create playlist
    playlist: str = spotify.create_playlist(title=playlist_name)
    
    # Add tracks to playlist!
    spotify.add_tracks_to_playlist(playlist, to_be_added)
    
    print("Done!")