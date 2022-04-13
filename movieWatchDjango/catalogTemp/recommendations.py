from .models import Movie, TVShow, Book, Podcast, PodcastEpisode, MovieRecommendation
from .movieWatchAPI import MovieRecommendationSerializer
from rest_framework.response import Response
from rest_framework.views import APIView


class AbstractReccommendThirdPartyObject(APIView):
    """
    This is for creating recommendation objects from third part apps.

    object_id_param - str the name that will be included with the request. This should be the third party ID not our
        internal IDs
    object_identifier_name - str the unique field in the Django model that will be used to find the object
    """
    object_id_param = None
    model_primary_key=None
    model = None
    model_serializer = MovieRecommendationSerializer

    def post(self, request, *args, **kwargs):
        """
        Actually posts the object if succesful
        :return:
        """
        recommendation_object = self.create_recommendation_object()
        serialized_data = self.model_serializer(recommendation_object)
        return Response(serialized_data.data)


    def create_recommendation_object(self, **kwargs):
        """
        Will create the actual recommendation object
        :param kwargs: additional arguments for recommendation object
        :return:
        """
        content_object = self.create_or_get_content_object()
        post_data = self.request.data
        rating = post_data['recommenderRating']
        desc = post_data['recommendationDesc']
        user = self.request.user
        if self.model_primary_key == 'tvID':
            args = {'tvShowID': content_object, "recommenderRating": rating,
                    "recommendationDesc": desc, "recommenderUserID": user, **kwargs}
        else:
            args = {self.model_primary_key:content_object, "recommenderRating":rating,
                "recommendationDesc":desc, "recommenderUserID":user, **kwargs}
        reccommendation = MovieRecommendation(**args)
        reccommendation.save()
        return reccommendation

    def create_or_get_content_object(self):
        """
        If the object doesn't already exist in our database, it will bec created and returned. If it does it will be
        returned.

        This will be need to be overwritten if the models has additional requiremtns for it's create_or_get_object()
            method
        :return: Django object of the content
        """
        print(str(self.get_object_id()))
        return self.model.get_or_create_object(id_value=self.get_object_id())

    def get_object_id(self):
        try:
            return self.request.data[self.object_id_param]
        except (KeyError, ValueError):
            self.permission_denied(self.request, message="Need to provide {0} with request".format(self.object_id_param))

class RecommendMovieV2(AbstractReccommendThirdPartyObject):
    object_id_param = 'movieID'
    model_primary_key = 'movieID'
    model = Movie

class RecommendTVShowV2(AbstractReccommendThirdPartyObject):
    object_id_param = 'tvShowID'
    model_primary_key = 'tvID'
    model = TVShow

class RecommendBookv2(AbstractReccommendThirdPartyObject):
    object_id_param = 'bookID'
    model_primary_key = 'bookID'
    model = Book

class RecommendPodcastv2(AbstractReccommendThirdPartyObject):
    object_id_param = 'podcastID'
    model_primary_key = 'podcastID'
    model = Podcast


class RecommendPodcastEpisodev2(AbstractReccommendThirdPartyObject):
    object_id_param = 'episodeID'
    model_primary_key = 'episodeID'
    model = PodcastEpisode
    podcast = None


    def post(self, request, *args, **kwargs):
        """
        Actually posts the object if succesful
        :return:
        """
        recommendation_object = self.create_recommendation_object(podcastID=self.get_or_get_and_create_podcast())
        serialized_data = self.model_serializer(recommendation_object)
        return Response(serialized_data.data)

    def create_or_get_content_object(self):
        podcast = self.get_or_get_and_create_podcast()
        episode_id = self.get_object_id()
        return PodcastEpisode.get_or_create_object(episode_id, podcast)

    def get_or_get_and_create_podcast(self):
        spotify_podcast_id = self.get_spotify_id()
        return Podcast.get_or_create_object(spotify_podcast_id)


    def get_spotify_id(self):
        try:
            return self.request.data['podcastID']
        except (KeyError, ValueError):
            self.permission_denied(self.request, message="Need to provide podcastID with request")
