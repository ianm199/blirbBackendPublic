from django.db import models
import uuid
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.conf import settings
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import random
import string
import tmdbsimple as tmdb
import re
from django.conf import settings
tmdb.API_KEY = settings.TMDB_API_KEY
#tmdb.API_KEY = "39644fd7924afa95564950208bfbf97f"

class ModelWithOwner(models.Model):
    """
    Extends model class to have an get_owner and get_group method so that it's compatible with the custom Permission classes
    """

    def get_owner(self):
        raise NotImplementedError

    def get_group(self):
        raise NotImplementedError

    class Meta:
        abstract = True

class ThirdPartyDataModel(models.Model):
    """
    Extends model class to add methods to standardize interacting with a third party data source. Abstract class that
    shouldn't be directly instantiated.

    Any class that inherits this needs to set third_party_identifier_field which indicates the key in the tabel that
    corresponds to the third party primary key we're copying - for movies and tv this would be tmdbID
    """
    third_party_identifier_field: str = None

    @classmethod
    def get_or_create_object(cls, id_value):
        try:
            kwargs = {cls.third_party_identifier_field: id_value}
            return cls.objects.get(**kwargs)
        except (models.ObjectDoesNotExist, cls.DoesNotExist) as e:
            kwargs = {'id':id_value}
            return cls.create_object_from_third_party_data_source(**kwargs)

    @classmethod
    def create_object_from_third_party_data_source(cls, id):
        """
        Needs to be implemented in each class
        """
        raise NotImplementedError

    class Meta:
        abstract = True


class UserDetails(ModelWithOwner):
    """
    Links one to one with the User model in order to add additional details to Users like phone numbers and whatnot
    """

    userDetailsID = models.AutoField(primary_key=True)
    userID = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, db_index=True)
    phoneNumber = models.BigIntegerField(unique=True, blank=True)

    def get_user(self):
        return self.userID



movieMappingDict = {"adult": "adult", "backdropPath": "backdrop_path", "genres": "genres",
                               "imdb_id": "imdb_id",
                               "original_language": "original_language",
                               "original_title": "original_title", "description": "overview",

                               "posterPath": "poster_path", "runtime":"runtime",
                               "releaseDate": "release_date", "status": "status",
                               "tagline": "tagline", "movieTitle":"title", "posterS3Key":"poster_path"}


class Movie(ThirdPartyDataModel):
    """
    Represents a movie
    """
    movieID = models.AutoField(primary_key=True)
    movieTitle = models.CharField(max_length=2048, help_text="Enter movie title")
    adult = models.BooleanField(default=False)
    description = models.TextField(max_length=2048, help_text="Enter description", blank=True)
    runtime = models.IntegerField(blank=True)
    backdropPath= models.TextField(max_length=2048, default=None, blank=True)
    genres = models.TextField(blank=True, default=None)
    tmdbID = models.IntegerField(default=None, blank=True, unique=True, db_index=True)
    imdb_id = models.CharField(max_length=512, default=None, blank=True)
    original_language = models.CharField(max_length=512, default=None, blank=True)
    original_title = models.CharField(max_length = 2048, default=None, blank=True)
    popularity = models.DecimalField(default=0.0,db_index=True, max_digits=12, decimal_places=10, blank=True)
    posterPath = models.TextField(max_length=4096, default=None, blank=True)
    releaseDate = models.DateField(default=None, blank=True)
    status = models.CharField(max_length=128, default=None, blank=True)
    tagline = models.TextField(max_length=2048, default="", blank=True)
    posterS3Key = models.CharField(max_length=2048, default="", blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_index=True)
    updatedAt = models.DateTimeField(auto_now=True)

    third_party_identifier_field = 'tmdbID'

    """    @classmethod
    def get_or_create_object(cls, tmdbID):
        try:
            return Movie.objects.get(tmdbID=tmdbID)
        except models.ObjectDoesNotExist:
            return Movie.create_movie_object_from_tmdb(int(tmdbID))"""

    @classmethod
    def create_object_from_third_party_data_source(cls, id):
        movie_dict = tmdb.Movies(id).info()
        kwargs = Movie.create_movie_kwargs(movie_dict)
        new_movie = Movie(tmdbID=id, **kwargs)
        new_movie.save()
        return new_movie

    @classmethod
    def create_movie_object_from_tmdb(cls, tmdbID: int):
        """
        Creates and saves a movie from TMDB
        :param tmdbID: tmdbID for the movie
        :return: Book object that has been created
        """
        movie_dict = tmdb.Movies(tmdbID).info()
        kwargs = Movie.create_movie_kwargs(movie_dict)
        new_movie = Movie(tmdbID=tmdbID, **kwargs)
        new_movie.save()
        return new_movie

    @classmethod
    def create_movie_kwargs(cls, tmdb_data_dict):
        Movie.parseGenreHelp(tmdb_data_dict)
        result = dict.fromkeys(movieMappingDict.keys())
        for key in movieMappingDict:
            value = movieMappingDict[key]
            result[key] = tmdb_data_dict[value]
        return result

    @staticmethod
    def parseGenreHelp(tmdb_dict):
        """
        TMDB genres comes as lists of genres dictionarys.. parsing this to just being a list of genres which will be converted to a string
        :param tmdb_dict:
        :return: Wont return anything , just changes the value of the dict
        """
        genres = tmdb_dict['genres']
        genresList = []
        for dict in genres:
            genre = dict['name']
            genresList.append(genre)
        tmdb_dict['genres'] = genresList

    @staticmethod
    def search_tmdb(query: str, page=1) -> list:
        """
        Perform a search from the TMDB API
        :param query: a query attach to TMDB endpoint
        :return: dict of results or an error if the query is invalid
        """
        search = tmdb.Search()
        responses = search.multi(query=query, include_adult=False, page=page)
        result = []
        for response in responses['results']:
            if response['media_type'] == 'movie' or response['media_type'] == 'tv':
                result.append(response)
        return result


    def __str__(self):
        return self.movieTitle

tvShowMappingDict = {"backdropPath": "backdrop_path", "firstAirDate":"first_air_date",
                     "inProduction":"in_production", "genres": "genres", "lastAirDate":"last_air_date",
                     "originCountry":"origin_country",
                     "showTitle":"name", "description": "overview",
                     "posterPath": "poster_path",  "posterS3Key":"poster_path", "tmdbID":"id"}

class TVShow(ThirdPartyDataModel):
    """
    Represents a tv series
    """
    tvID = models.AutoField(primary_key=True)
    backdropPath = models.TextField(max_length=2048, default=None, blank=True, null=True)
    firstAirDate = models.DateField(default=None, blank=True, null=True)
    genres = models.TextField(max_length=2048, default="")
    tmdbID = models.IntegerField(default=None, blank=True, unique=True)
    inProduction = models.BooleanField(default=False)
    lastAirDate = models.DateField(default=None, blank=True, null=True)
    showTitle=models.TextField(max_length=4086, blank=True, default=None)
    description = models.TextField(max_length=8192, blank=True, default="")
    popularity = models.DecimalField(default=0.0,db_index=True, max_digits=12, decimal_places=10, blank=True)
    posterPath = models.TextField(max_length=2048, default="", blank=True, null=True)
    showType = models.TextField(max_length=256, default="", blank=True)
    originCountry = models.TextField(max_length=256, default="", blank=True)
    posterS3Key = models.CharField(max_length=2048, default="", blank=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_index=True)
    updatedAt = models.DateTimeField(auto_now=True)

    third_party_identifier_field = "tmdbID"

    @classmethod
    def create_object_from_third_party_data_source(cls, id):
        return TVShow.create_tvshow_object_from_tmdb(id)


    @classmethod
    def create_tvshow_object_from_tmdb(cls, tmdbID: int):
        """
        Creates and saves a tv show from TMDB
        :param tmdbID: tmdbID for the movie
        :return: TVShow object that has been created
        """
        tv_dict = tmdb.TV(tmdbID).info()
        kwargs = TVShow.create_tv_kwargs(tv_dict)
        new_show = TVShow(**kwargs)
        new_show.save()
        return new_show

    @classmethod
    def create_tv_kwargs(cls, tmdb_data_dict):
        TVShow.parseGenreHelp(tmdb_data_dict)
        result = dict.fromkeys(tvShowMappingDict.keys())
        for key in tvShowMappingDict:
            if key == "tmdbID":
                value = tvShowMappingDict[key]
                result[key] = int(tmdb_data_dict[value])
            elif key == "episodeRunTime":
                value = tvShowMappingDict[key]
                if not value:
                    result[key] = 0
                else:
                    result[key] = int(tmdb_data_dict[value][0])
            elif key == "backdropPath":
                value = tvShowMappingDict[key]
                if value is None:
                    result[key]="None"
                else:
                    result[key] = "test"
            else:
                value = tvShowMappingDict[key]
                result[key] = tmdb_data_dict[value]
        return result

    @staticmethod
    def parseGenreHelp(tmdb_dict):
        """
        TMDB genres comes as lists of genres dictionarys.. parsing this to just being a list of genres which will be converted to a string
        :param tmdb_dict:
        :return: Wont return anything , just changes the value of the dict
        """
        genres = tmdb_dict['genres']
        genresList = []
        for dict in genres:
            genre = dict['name']
            genresList.append(genre)
        tmdb_dict['genres'] = genresList


class Book(ThirdPartyDataModel):
    """
    This model represents information from google books API that is saved. Can only be one instance of each book.
    Books get saved when a user recommends them.
    """
    bookID = models.AutoField(primary_key=True)
    googleBookID = models.CharField(max_length=255, null=False, blank=False, unique=True)
    bookTitle = models.CharField(max_length=4096, default=None, blank=False, null=False)
    authors = models.CharField(max_length=8192, default="")
    publisher = models.TextField(max_length=8192, default="")
    description = models.TextField(max_length=16384, default="")
    pageCount = models.IntegerField(default=None, blank=True, null=True)
    categories = models.TextField(max_length=4096, default="", blank=True, null=True)
    thumbnail = models.TextField(max_length=4096, default="", blank=True, null=True)
    language = models.TextField(max_length=128, default="", blank=True, null=True)
    infoLink = models.TextField(max_length=4096, default="", blank=True, null=True)
    previewLink = models.TextField(max_length=4096, default="", blank=True, null=True)
    canonicalVolumeLink = models.TextField(max_length=4096, default="", blank=True, null=True)

    third_party_identifier_field = "googleBookID"

    @classmethod
    def create_object_from_third_party_data_source(cls, id):
        return Book.create_book_object_from_google_api(id)

    @classmethod
    def get_book_dict(self, google_book_id, api_key=''):
        """
        Get data dict from google books api for a specific volume
        :param google_book_id: id that matches book. When you get results from google books it will be in 'id' field
        :return: dict with all info pertaining to a book
        """
        request_url = 'https://www.googleapis.com/books/v1/volumes/{0}?API_KEY={1}'.format(google_book_id, api_key)
        request = requests.get(request_url)
        return request.json()


    @classmethod
    def create_book_object_from_google_api(cls, google_book_id):
        """
        Creates and saves a book from a google volume dict
        :param google_volume_dict: dict object that is returned from google books volume endpoint
        :return: will return the book created
        """
        google_volume_dict = Book.get_book_dict(google_book_id)
        id = google_volume_dict['id']
        if Book.objects.filter(googleBookID=id).exists():
            return Book.objects.get(googleBookID=id)
        volume_info = google_volume_dict['volumeInfo']
        kwargs: dict = Book.create_kwargs(volume_info)
        new_book = Book(googleBookID=id, bookTitle=volume_info.get("title", "N/A"), authors=str(volume_info.get("authors", "N/A")),
                         description=Book.get_description(volume_info),
                        categories=Book.get_categories(volume_info), thumbnail=Book.get_thumbnail(volume_info), **kwargs)
        new_book.save()
        return new_book

    @staticmethod
    def cleanhtml(raw_html):
        cleanr = re.compile('<.*?>')
        cleantext = re.sub(cleanr, '', raw_html)
        return cleantext

    @staticmethod
    def create_kwargs(volume_dict: dict) -> dict:
        volume_info_args = ['publisher', 'pageCount', 'language', 'infoLink', 'previewLink',
                            'canonicalVolumeLink']
        result = {}
        for arg in volume_info_args:
            try:
                result[arg] = volume_dict[arg]
            except KeyError as e:
                if arg == 'pageCount':
                    result[arg] = 0
                else:
                    result[arg] = ""
        return result

    @staticmethod
    def get_description(volume_dict):
        try:
            return Book.cleanhtml(volume_dict['description'])
        except KeyError:
            return ""

    @staticmethod
    def get_categories(volume_dict):
        try:
            return str(volume_dict['categories'])
        except KeyError:
            return ""

    @staticmethod
    def get_thumbnail(volume_dict):
        try:
            return volume_dict['imageLinks']['thumbnail']
        except KeyError:
            return ""

class Podcast(ThirdPartyDataModel):
    """
    Represents information about a podcast. Information comes from Spotify API and is created when a user recommends it.
    """

    #TODO: Refactor Spotify and google credentials to not be in source control

    SPOTIFY_MARKETS = ['AD', 'AE', 'AR', 'AT', 'AU', 'BE', 'BG', 'BH', 'BO', 'BR', 'CA', 'CH', 'CL', 'CO', 'CR', 'CY',
                       'CZ',
                       'DE', 'DK', 'DO', 'DZ', 'EC', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'GT', 'HK', 'HN', 'HU', 'ID',
                       'IE',
                       'IL', 'IN', 'IS', 'IT', 'JO', 'JP', 'KW', 'LB', 'LI', 'LT', 'LU', 'LV', 'MA', 'MC', 'MT', 'MX',
                       'MY',
                       'NI', 'NL', 'NO', 'NZ', 'OM', 'PA', 'PE', 'PH', 'PL', 'PS', 'PT', 'PY', 'QA', 'RO', 'SE', 'SG',
                       'SK',
                       'SV', 'TH', 'TN', 'TR', 'TW', 'US', 'UY', 'VN', 'ZA']
    SPOTIFY_CID = '05df2b3fe1f94a85a5157a9e17c3b193'
    SPOTIFY_SECRET = '1d3521cc844b47718b34eaf5a4219385'

    podcastID = models.AutoField(primary_key=True)
    spotifyPodcastID = models.CharField(max_length=255, null=False, blank=False, unique=True)
    description = models.TextField(max_length=8192, default="")
    spotifyURL = models.TextField(max_length=4096, default="", blank=True, null=True)
    spotifyImageURL = models.TextField(max_length=512, default="", blank=True)
    adult = models.TextField(max_length=128, default="False", blank=False)
    title = models.TextField(max_length=8192, default=None, blank=False)
    publisher = models.TextField(max_length=8192, default="", blank=True)


    third_party_identifier_field = "spotifyPodcastID"

    @classmethod
    def create_object_from_third_party_data_source(cls, id):
        return Podcast.create_podcast_from_spotify_api(id)


    @classmethod
    def create_podcast_from_spotify_api(cls, show_id):
        """
        Creates and returns a podcast
        object from spotify API. If the podcast is already in the database
        it will just return that object
        :param id: id that corresponds to the id in Spotify
        :return: Podcast object that corresponds to the id provided
        """
        if Podcast.objects.filter(spotifyPodcastID=show_id).exists():
            return Podcast.objects.get(spotifyPodcastID=show_id)
        show_data = Podcast.get_spotify_show_data(show_id)
        new_podcast = Podcast(spotifyPodcastID=show_data['id'], description=show_data['description'],
                              spotifyURL=show_data['external_urls']['spotify'], spotifyImageURL=show_data['images'][0]['url'],
                              adult=show_data['explicit'], title=show_data['name'], publisher=show_data['publisher'])
        new_podcast.save()
        return new_podcast


    @classmethod
    def get_spotify_show_data(cls, show_id):
        """
        Gets the show data for a spotify
        :param show_id: id that corresponds to Spotify show
        :return: dict containg spotify data about show
        """
        spotify_client = cls.get_spotipy_client()
        show_data = spotify_client.show(show_id=show_id, market=cls.SPOTIFY_MARKETS)
        return show_data

    @classmethod
    def get_spotipy_client(cls):
        client_credentials_manager = SpotifyClientCredentials(client_id=cls.SPOTIFY_CID, client_secret=cls.SPOTIFY_SECRET)
        spotify_client = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        return spotify_client

    def get_show_episodes(self, limit=50, offset=0):
        """
        Get info on episodes
        :return: list of dict of info on the shows episodes
        """
        spotify_client = self.get_spotipy_client()
        episode_data = spotify_client.show_episodes(show_id=self.spotifyPodcastID, market=self.SPOTIFY_MARKETS, limit=limit, offset=offset)
        return episode_data

    @classmethod
    def get_show_episodes_by_spotify_id(cls, show_id, limit=50, offset=0):
        spotify_client = cls.get_spotipy_client()
        episode_data = spotify_client.show_episodes(show_id=show_id, market=cls.SPOTIFY_MARKETS, limit=limit, offset=offset)
        return episode_data



class PodcastEpisode(ThirdPartyDataModel):

    episodeID = models.AutoField(primary_key=True)
    audioPreviewURL = models.TextField(max_length=255, default="", blank=True, null=True)
    description = models.TextField(max_length=16120, default="", blank=True, null=True)
    duration_ms = models.TextField(max_length=255, default="0", blank=True, null=True)
    explicit = models.BooleanField(default="False")
    spotifyURL = models.TextField(max_length=512, default=None, blank=True, null=True)
    spotifyID = models.CharField(max_length=255, null=False, blank=False, unique=True)
    spotifyImageURL = models.TextField(max_length=512, default="", blank=True)
    name = models.TextField(max_length=4012, default="", blank=True)
    release_date = models.TextField(max_length=127, default="NA", blank=True)
    podcastID = models.ForeignKey('Podcast', default=None, blank=False, on_delete=models.CASCADE)

    third_party_identifier_field = "spotifyID"

    @classmethod
    def get_or_create_object(cls, episode_id, podcast: Podcast):
        """
        Leaving this as is due to extra complexity with podcast episodes. Might revisit later
        """
        try:
            return PodcastEpisode.objects.get(spotifyID=episode_id)
        except models.ObjectDoesNotExist:
            return PodcastEpisode.create_object_from_external_api(episode_id, podcast)

    @classmethod
    def create_object_from_external_api(cls, episode_id, podcast: Podcast):
        episode_data = PodcastEpisode.get_episode_data(episode_id)
        episode = PodcastEpisode(audioPreviewURL=episode_data['audio_preview_url'],description=episode_data['description'],
                                 duration_ms=episode_data['duration_ms'], explicit=episode_data['explicit'],
                                 spotifyURL=episode_data['external_urls']['spotify'],
                                 spotifyImageURL=episode_data['images'][0]['url'],
                                 spotifyID=episode_data['id'],
                                 name=episode_data['name'],
                                 release_date=episode_data['release_date'], podcastID=podcast)
        episode.save()
        return episode

    @classmethod
    def get_episode_data(cls, episode_id):
        client = Podcast.get_spotipy_client()
        return client.episode(episode_id=episode_id, market=Podcast.SPOTIFY_MARKETS)


class MovieRecommendation(models.Model):
    """
    Represents a recommendation made by a user of multiple media types... didnt rename from movierec because django makes
    it a pain. Data validation enforced by clean
    """
    # TODO: Come back to this - add streaming options
    movieRecID = models.AutoField(db_column="movieRecID", primary_key=True)
    movieID = models.ForeignKey('Movie',  related_name="movie", on_delete=models.CASCADE, null=True, blank=True)
    tvShowID = models.ForeignKey('TVShow', related_name="TV", on_delete=models.CASCADE, null=True, blank=True)
    bookID = models.ForeignKey('Book', related_name='book2', on_delete=models.CASCADE, null=True, blank=True)
    podcastID = models.ForeignKey('Podcast', related_name="pod", on_delete=models.CASCADE, null=True, blank=True)
    episodeID = models.ForeignKey('PodcastEpisode', related_name='episode', on_delete=models.CASCADE, null=True,
                                  blank=True)
    recommenderUserID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    recommendationDesc = models.CharField(max_length=2048, help_text="Enter reccomendation")
    recommenderRating = models.IntegerField(help_text="Enter rating")
    createdAt = models.DateTimeField(auto_now_add=True, db_index=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def get_owner(self):
        return self.recommenderUserID

    class Meta:
        ordering = ['createdAt']

    def __str__(self):
        # TODO: Figure out how to get movie title from this
        if self.movieID is not None:
            return self.movieID.movieTitle
        elif self.tvShowID is not None:
            return self.tvShowID.showTitle
        elif self.bookID is not None:
            return self.bookID.bookTitle
        elif self.podcastID is not None:
            if self.episodeID is not None:
                return self.episodeID.name
            else:
                return self.podcastID.title




class MovieRecommendationWithinGroup(models.Model):
    """
    Represents a recommendation of several different media types...
    didn't rename because it's kind of a pain with django
    """
    groupRecID = models.AutoField(primary_key=True)
    recID = models.ForeignKey('MovieRecommendation', on_delete=models.CASCADE, null=True)
    memberID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False)
    groupID = models.ForeignKey('UserGroup', on_delete=models.CASCADE, null=True)
    createdAt = models.DateTimeField(auto_now_add=True, db_index=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def get_group(self):
        return self.groupID

    def get_owner(self):
        return self.memberID

    class Meta:
        ordering = ['createdAt']
        unique_together = ['recID', 'groupID']

class CommentOnGroupMovieRecommendation(models.Model):
    """
    Model for comments.
    To clarify - postID the movieRecInGroup they correspond to to
    commentResponseID - the comment a subcomment directly replys to
    commentParentID - the comment a subcomment is under
    """
    commentID = models.AutoField(primary_key=True)
    postID = models.ForeignKey('MovieRecommendationWithinGroup', on_delete=models.CASCADE, null=True)
    commentUserID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    commentBody = models.CharField(max_length=8192, default="")
    commentResponseID = models.IntegerField(default=0, null=True)
    commentParentID = models.IntegerField(default=0, null=True)
    commentDepth = models.IntegerField(default=0, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def get_group(self):
        return self.postID.groupID

    def get_owner(self):
        return self.commentUserID

    def delete_comment(self):
        """
        Deleting a comment will replace the comment with user "removed"
        :return: If delete goes properly will return new comment
        """
        removed_user = CommentOnGroupMovieRecommendation.get_or_create_removed_user()
        self.commentBody = ""
        self.commentUserID = removed_user
        self.save()
        return self

    class Meta:
        ordering = ['createdAt']

    @staticmethod
    def get_or_create_removed_user():
        if User.objects.filter(username="removed").exists():
            return User.objects.get(username="removed")
        else:
            new_user = User(first_name="Removed", last_name="User", username="removed", email="removed@removed123.com")
            new_user.save()
            new_user_details = UserDetails(userID=new_user, phoneNumber="5052305555")
            new_user_details.save()
            return new_user

class UserGroup(models.Model):
    """
    Represents groups of users
    """
    groupID = models.AutoField(primary_key=True)
    groupName = models.CharField(max_length=512, help_text="Enter group name")
    groupDesc = models.CharField(max_length=2048, help_text="Enter group description")
    createrUserID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    groupJoinCode = models.CharField(max_length=128, db_index=True, default=None, unique=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def get_owner(self):
        return self.createrUserID

    def __str__(self):
        return self.groupName

    def add_user_to_group(self, user: User):
        """
        Adds a user to the group
        :param user: Django user object to be added
        :return: GroupMember object will be returned that is the group and the user
        """
        new_group_member = GroupMembers(groupID=self, userID=user)
        new_group_member.save()
        return new_group_member

    def user_in_group(self, user) -> bool:
        """
        Returns whether or not a user is in a group
        :param user: Django user object
        :return: boolean whether or not they're in the group
        """
        return GroupMembers.objects.filter(groupID=self, userID=user).exists()


    @staticmethod
    def get_random_string(length):
        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(length))
        return result_str


    def generate_group_join_code(self):
        random_string = UserGroup.get_random_string(8)
        self.groupJoinCode = random_string
        self.save()


    def save(self, *args, **kwargs):
        """
        Overwritten so that user group codes will be created automatically
        """
        super(UserGroup, self).save(*args, **kwargs)

class GroupMembers(models.Model):
    """
    Represents user-group combinations
    """
    groupMemberID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    groupID = models.ForeignKey('UserGroup', on_delete=models.CASCADE, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['userID', 'groupID']



class UserProfile(models.Model):
    """
    Represents a user profile
    """
    id = models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=512)
    body = models.CharField(max_length=512)
    profilePicture = models.CharField(max_length=1024)

class EndorsementsOnMovieRecsInGroups(models.Model):
    """
    Represents someone in a group endorsing a movie rec someone else makes
    """
    endorsementID = models.AutoField(primary_key=True)
    endorserUserID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    recID = models.ForeignKey('MovieRecommendation', on_delete=models.CASCADE, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)

    def get_group(self):
        return self.postID.groupID

    def get_owner(self):
        return self.endorserUserID

    class Meta:
        unique_together = [['endorserUserID','recID']]

class LikesOnCommentsOnPosts(models.Model):
    """
    Allows people to like comments on posts
    """

    likeID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    commentID = models.ForeignKey('CommentOnGroupMovieRecommendation', on_delete=models.CASCADE, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)

    def get_group(self):
        return self.commentID.postID.groupID

    def get_owner(self):
        return self.userID

    class Meta:
        unique_together = ['userID', 'commentID']

class GroupProfilePictures(models.Model):
    """
    Stores data for group profile pictures. For now, groups will be able to have multiple and
    what will be selected is their latest
    """
    groupPicID = models.AutoField(primary_key=True)
    groupID = models.ForeignKey('UserGroup', on_delete=models.CASCADE, null=False, db_index=True)
    fileName= models.CharField(max_length=2048, default=None)
    S3Key = models.CharField(max_length=2048, default=None)
    createdAt = models.DateTimeField(auto_now_add=True)

    def get_group(self):
        return self.groupID

from rest_framework.request import Request
class UserProfilePictures(models.Model):
    """
    Stores data for user profile pictures
    """
    userProPicID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False)
    fileName = models.CharField(max_length=2048, default=None)
    S3Key = models.CharField(max_length=2048, default=None)
    createdAt = models.DateTimeField(auto_now_add=True)

    def get_owner(self):
        return self.userID

    @classmethod
    def generate_or_get_s3_Key(cls, request: Request) -> str:
        """
        Generates of gets an s3 key for the users profile picture
        """
        try:
            s3_key = UserProfilePictures.objects.get(userID=request.user).S3Key
        except models.ObjectDoesNotExist as e:
            s3_key = "user-profile-pics/" + str(request.user.id) + str(random.random())
        return s3_key

class UserNotifications(models.Model):
    """
    Stores data for user notifications
    """
    notificationID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, related_name="senderUserID",
                               on_delete=models.CASCADE, null=False, blank=True, default=None)
    receiverUserID = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True,related_name="receiverUserID",
                                       on_delete=models.CASCADE, null=False,  default=None, blank=True)
    notificationDescription = models.TextField(max_length=8192, default=None)
    groupRecID = models.ForeignKey('MovieRecommendationWithinGroup', on_delete=models.CASCADE, null=True, blank=True,
                                   default=None)
    commentID = models.ForeignKey('CommentOnGroupMovieRecommendation', db_index=True, related_name="receiverUserID",
                                       on_delete=models.CASCADE, null=True, default=None, blank=True)
    notificationSeen = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)

class CastOfMovies(models.Model):
    """
    Represents a cast member in a movie
    """
    castMovieID = models.AutoField(primary_key=True)
    movieID = models.IntegerField(blank=True, default=None)
    tmdbMovieID = models.IntegerField(default=None, blank=False, null=False, db_index=True)
    tmdbCastID = models.IntegerField(default=None, blank=False, null=False)
    characterName = models.CharField(max_length=2098, default=None, blank=True)
    creditID = models.TextField(max_length=2098, default=None, blank=True)
    gender = models.IntegerField(default=None, blank=True)
    tmdbID2 = models.IntegerField(default=None, blank=True)
    actorName = models.CharField(max_length=2098, default=None, blank=True)
    orderOfCast = models.IntegerField(default=None, blank=True)
    profile_path = models.CharField(max_length=2048, default=None, blank=True)

class UserRankings(models.Model):
    """
    Represents a ranking set a user can make
    """
    rankingsID = models.AutoField(primary_key=True)
    nameOfRankings = models.TextField(max_length=512, blank=False, null=False)
    ordered = models.BooleanField(default=False)
    creatorUserID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, db_index=True)
    createdAt = models.DateTimeField(auto_now=True)
    rankingsS3Key = models.TextField(max_length=512, blank=True, null=True)
    publicToGroups = models.BooleanField(default=True)

    def get_owner(self):
        return self.creatorUserID



class RankingsItems(models.Model):
    """
    Represents items within rankings list. Can add content types as they expand.
    """
    rankingItemID = models.AutoField(primary_key=True)
    rankingList = models.ForeignKey('UserRankings', related_name="ranking", on_delete=models.CASCADE, null=True, blank=False, db_index=True)
    movieID = models.ForeignKey('Movie', related_name="movieitem", on_delete=models.CASCADE, null=True, blank=True)
    tvShowID = models.ForeignKey('TVShow', related_name="TVitem", on_delete=models.CASCADE, null=True, blank=True)
    bookID = models.ForeignKey('Book', related_name="book", on_delete=models.CASCADE, null=True, blank=True)
    podcastID = models.ForeignKey('Podcast', related_name="podcast", on_delete=models.CASCADE, null=True, blank=True)
    episodeID = models.ForeignKey('PodcastEpisode', related_name="ep", on_delete=models.CASCADE, null=True, blank=True)
    rankingInList = models.IntegerField(default=0, blank=False)
    rankingsDescription = models.TextField(max_length=2024, default=None, blank=True, null=True)

    def get_owner(self):
        return self.rankingList.creatorUserID

    class Meta:
        unique_together = [['movieID', 'rankingList'], ['tvShowID', 'rankingList'],
                           ['bookID', 'rankingList'], ['episodeID', 'rankingList']]



class GroupChatPictures(models.Model):
    """
    Represents groupchats in pictures
    """
    groupchatPicID= models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False)
    groupID = models.ForeignKey('UserGroup', on_delete=models.CASCADE, null=False, db_index=True)
    fileName = models.CharField(max_length=2048, default=None)
    S3Key = models.CharField(max_length=2048, default=None)
    createdAt = models.DateTimeField(auto_now_add=True)

    def get_group(self):
        return self.groupID

    def get_owner(self):
        return self.userID

class OverallFeedExclusions(ModelWithOwner):
    """
    This is used to filter out groups people are in from the main feed
    """
    exclusionID = models.AutoField(primary_key=True)
    userID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, db_index=True)
    groupID = models.ForeignKey('UserGroup', on_delete=models.CASCADE, null=False)
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['userID', 'groupID']

    def get_owner(self):
        return self.userID

    def get_group(self):
        return self.groupID

class Report(models.Model):
    """
    This is used to make reports on posts and comments
    """
    reportID = models.AutoField(primary_key=True)
    commentID = models.ForeignKey('CommentOnGroupMovieRecommendation', on_delete=models.CASCADE, null=True, blank=True)
    groupRecID = models.ForeignKey('MovieRecommendationWithinGroup', on_delete=models.CASCADE, null=True, blank=True)
    reportComment = models.CharField(max_length=4096, blank=True, null=True)
    reporterUserID = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, db_index=True)
    createdAt = models.DateTimeField(auto_now_add=True)


class SignUpCode(models.Model):
    """
    This model will allow users to join a group or several groups at once upon signing up
    """

    codeID = models.AutoField(primary_key=True)
    signUpCode = models.CharField(max_length=255, blank=False, default=None, unique=True)

    def add_user_to_sign_up_groups(self, user: User):
        """
        Add user to all the groups related to a sign up code
        :param user: django user object who will join te groups
        :return: N/A user will be added to groups
        """
        sign_up_groups = SignUpCodeGroups.objects.filter(codeID=self.codeID)
        for group in sign_up_groups:
            group.groupID.add_user_to_group(user)

class SignUpCodeGroups(models.Model):
    """
    This manages the groups an individual sign up group corresponds to
    """

    signUpGroupID = models.AutoField(primary_key=True)
    groupID = groupID = models.ForeignKey('UserGroup', on_delete=models.CASCADE, blank=False, default=None)
    codeID = models.ForeignKey('SignUpCode', on_delete=models.CASCADE, blank=False, default=None)



class File(models.Model):
    file = models.FileField(blank=False, null=False)

    def __str__(self):
        return self.file.name
