from .models import Podcast, Movie
from rest_framework.response import Response
from rest_framework.views import APIView
import spotipy
from spotipy import SpotifyClientCredentials
import requests
from rest_framework.pagination import _positive_int
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.request import Request
from django.conf import settings


SEARCH_PODCASTS_ENDPOINT = 'podcasts/search/'
search_books_endpoint = 'books/search/'
get_podcasts_episodes_endpoint = 'podcasts/episodes/'


@api_view(["GET"])
def search_tmdb(request: Request, *args, **kwargs):
    query_params = request.query_params
    if "query" not in query_params:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error": "Missing parameter query"})
    if 'page' in query_params:
        page=int(query_params['page'])
    else:
        page=1
    return Response(status=status.HTTP_200_OK, data={"Content": Movie.search_tmdb(query_params['query'], page=page)})


class SearchSpotifyPodcasts(APIView):

    query_param = 'q'
    limit_param = 'limit'
    offset_query_param = 'offset'
    DEFAULT_PAGE_LIMIT = 10
    DEFAULT_OFFSET = 0
    base_endpoint = SEARCH_PODCASTS_ENDPOINT

    def get(self, request, *args, **kwargs):
        spotify_data = self.search_spotify_podcasts()
        return Response(spotify_data)

    def search_spotify_podcasts(self):
        cid = settings.SPOTIFY_CID
        secret = settings.SPOTIFY_SECRET
        #cid = '05df2b3fe1f94a85a5157a9e17c3b193'
        #secret = '1d3521cc844b47718b34eaf5a4219385'
        client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
        spotify_client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        self.query_term = self.get_query_term()
        self.limit = self.get_limit()
        self.offset = self.get_offset()
        search_data = spotify_client.search(q=self.query_term, market=Podcast.SPOTIFY_MARKETS,
                                            type='show', limit=self.limit, offset=self.offset)
        shows = search_data['shows']['items']
        shows.append({"next":self.build_next()})
        return shows

    def build_next(self):
        full_url = self.base_endpoint + '?q="{0}"&limit={1}&offset={2}'
        next_offset = int(self.offset) + int(self.limit)
        next_url = full_url.format(self.query_term, self.limit, next_offset)
        return next_url

    def get_query_term(self):
        try:
            return self.request.query_params[self.query_param]
        except (ValueError, KeyError):
            self.permission_denied(self.request, message="Missing query parameter")

    def get_limit(self):
        try:
            return self.request.query_params[self.limit_param]
        except (ValueError, KeyError):
            return self.DEFAULT_PAGE_LIMIT

    def get_offset(self):
        try:
            return self.request.query_params[self.offset_query_param]
        except (ValueError, KeyError):
            return self.DEFAULT_OFFSET


class SearchGoogleBooksAPI(APIView):

    query_param = 'q'
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    api_key = settings.GOOGLE_API_KEY
    #api_key = 'AIzaSyDHSdYKzmHzCIIDlrS3iWp3HQf4w-e54iQ'
    base_endpoint = search_books_endpoint
    DEFAULT_PAGE_LIMIT = 40
    DEFAULT_OFFSET = 0

    def get(self, request, *args, **kwargs):
        request_url = self.build_url()
        try:
            results = requests.get(request_url)
        except (TimeoutError, ConnectionError):
            self.permission_denied(self.request, message="Error accessing third party API")
        except Exception:
            self.permission_denied(self.request, message="Unexpected error when accesing third party API")
        json_response = results.json()
        json_response['next'] = self.build_next()
        SearchGoogleBooksAPI.add_https(json_response)
        return Response(json_response)

    @staticmethod
    def add_https(response) -> None:
        """
        Changes the google books links from http to https
        Candidate to refactor
        """
        books = response['items']
        for book in books:
            try:
                book['accessInfo']['webReaderLink'] = SearchGoogleBooksAPI.http_to_https(book['accessInfo']['webReaderLink'])
            except KeyError as e:
                pass
            try:
                book['accessInfo']['epub']['acsTokenLink'] = SearchGoogleBooksAPI.http_to_https(book['accessInfo']['epub']['acsTokenLink'])
            except KeyError as e:
                pass
            try:
                book['accessInfo']['webReaderLink'] = SearchGoogleBooksAPI.http_to_https(book['accessInfo']['webReaderLink'])
            except KeyError as e:
                pass
            try:
                book['volumeInfo']['imageLinks']['smallThumbnail'] = SearchGoogleBooksAPI.http_to_https(book['volumeInfo']['imageLinks']['smallThumbnail'])
            except KeyError as e:
                pass
            try:
                book['volumeInfo']['imageLinks']['thumbnail'] = SearchGoogleBooksAPI.http_to_https(book['volumeInfo']['imageLinks']['thumbnail'])
            except KeyError as e:
                pass
            try:
                book['volumeInfo']['previewLink'] = SearchGoogleBooksAPI.http_to_https(book['volumeInfo']['previewLink'])
            except KeyError as e:
                pass

    @staticmethod
    def http_to_https(link: str) -> str:
        """
        Turns http -> https if the link starts with 'http'
        """
        if link.startswith('http') and not link.startswith("https"):
            link = link[0:4] + "s" + link[4:]
            return link


    def build_url(self):
        #TODO: Refactor later
        query_params = self.request.query_params
        base_url = 'https://www.googleapis.com/books/v1/volumes?q=' + self.get_query_term()
        if 'limit' in query_params:
            limit = _positive_int(query_params['limit'])
            self.limit = limit
            base_url += '&maxResults={0}'.format(limit)
        if 'offset' in query_params:
            offset = _positive_int(query_params['offset'])
            self.offset = offset
            base_url += '&startIndex={0}'.format(offset)
        final_url = base_url + '&API_KEY=' + self.api_key
        return final_url

    def get_limit(self):
        try:
            return self.request.query_params[self.limit_query_param]
        except (ValueError, KeyError):
            return self.DEFAULT_PAGE_LIMIT

    def get_offset(self):
        try:
            return self.request.query_params[self.offset_query_param]
        except (ValueError, KeyError):
            return self.DEFAULT_OFFSET


    def get_query_term(self):
        try:
            self.query_term = self.request.query_params[self.query_param]
            return self.query_term
        except (ValueError, KeyError):
            self.permission_denied(self.request, message="Missing query parameter")

    def build_next(self):
        full_url = self.base_endpoint + '?q="{0}"&limit={1}&offset={2}'
        limit = self.get_limit()
        offset = self.get_offset()
        next_offset = int(limit) + int(offset)
        next_url = full_url.format(self.get_query_term(), limit, next_offset)
        return next_url
