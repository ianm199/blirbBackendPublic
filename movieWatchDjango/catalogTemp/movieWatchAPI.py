from rest_framework import serializers
from .models import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView



class MovieSerializer(serializers.HyperlinkedModelSerializer):
    """
    Class to serialize movies for API
    """
    class Meta:
        model = Movie
        fields = ['movieID', 'movieTitle', 'description', 'runtime',
                  'genres', 'releaseDate', 'popularity', 'tagline', 'status', 'posterS3Key']

class TVSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializes TVShow data
    """
    class Meta:
        model = TVShow
        fields = ['tvID', 'showTitle', 'description', 'numberEpisodes',
                  'numberSeasons', 'popularity', 'status', 'inProduction', 'episodeRunTime', 'posterS3Key']

class MovieRecommendationSerializer(serializers.HyperlinkedModelSerializer):
    recommenderUserID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    movieID = serializers.PrimaryKeyRelatedField(many=False, queryset=Movie.objects.all(), required=False)
    tvShowID = serializers.PrimaryKeyRelatedField(many=False, queryset=TVShow.objects.all(), required=False)
    bookID = serializers.PrimaryKeyRelatedField(many=False, queryset=Book.objects.all(), required=False)
    podcastID = serializers.PrimaryKeyRelatedField(many=False, queryset=Podcast.objects.all(), required=False)

    class Meta:
        model = MovieRecommendation
        fields = ['movieRecID', 'tvShowID', 'movieID', 'bookID', 'podcastID', 'recommenderUserID',
                  'recommendationDesc', 'recommenderRating', 'createdAt', 'updatedAt']
        ordering = ['createdAt']

    def validate(self, attrs):
        """
        Overwritten in order to enforce either movieID or tvShowID being null, but not both
        """
        return validate_multimedia(attrs)

class MovieRecommendationSerializerTest(serializers.HyperlinkedModelSerializer):
    recommenderUserID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    movieID = MovieSerializer(source='movieID')
    tvShowID = serializers.PrimaryKeyRelatedField(many=False, queryset=TVShow.objects.all(), required=False)

    class Meta:
        model = MovieRecommendation
        fields = ['movieRecID', 'tvShowID', 'movieID', 'bookID', 'recommenderUserID', 'recommendationDesc', 'reccomenderRating',
                  'createdAt', 'updatedAt']
        ordering = ['createdAt']

    def validate(self, attrs):
        """
        Overwritten in order to enforce either movieID or tvShowID being null, but not both
        """
        if 'movieID' in attrs and 'tvShowID' in attrs:
            raise serializers.ValidationError("Cannot have both tvShowID and movieID in one rec")
        elif 'movieID' not in attrs and 'tvShowID' not in attrs:
            raise serializers.ValidationError("Need either a movieId or a tvShowID in rec")
        return attrs


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User

        fields = ['id', 'is_superuser', 'username', 'first_name', 'last_name', 'password', 'email']

    def create(self, validated_data):
        """
        Overwridden to properly encrypt passwords
        """
        user = User()
        user.set_password(validated_data['password'])
        user.username = validated_data['username']
        user.first_name = validated_data['first_name']
        user.last_name = validated_data['last_name']
        user.email = validated_data['email']
        user.save()
        return user

class PublicUserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['id','username', 'first_name', 'last_name']

class PublicUserSerializerCustom(serializers.HyperlinkedModelSerializer):
    """
    Made to include email in currentuserinfo
    """
    class Meta:
        model = User
        fields = ['id','username', 'first_name', 'last_name', 'email']



class Logout(APIView):
    def get(self, request, format=None):
        # simply delete the token to force a login
        request.user.auth_token.delete()
        return Response(status=status.HTTP_200_OK)

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    createrUserID = serializers.PrimaryKeyRelatedField( read_only=True,
                                                       default=serializers.CurrentUserDefault())
    class Meta:
        model = UserGroup
        fields = ['groupID', 'groupName', 'groupDesc', 'createrUserID', 'groupJoinCode', 'createdAt', 'updatedAt']



class GroupMemberSerialzier(serializers.HyperlinkedModelSerializer):
    userID = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=False)
    groupID = serializers.PrimaryKeyRelatedField(
        queryset=UserGroup.objects.all(),
        many=False)
    class Meta:
        model = GroupMembers
        fields = ['groupMemberID', 'userID', 'groupID', 'createdAt']

class MovieRecInGroupSerializer(serializers.HyperlinkedModelSerializer):
    recID = serializers.PrimaryKeyRelatedField(queryset=MovieRecommendation.objects.all(), many=False)
    groupID = serializers.PrimaryKeyRelatedField(queryset=UserGroup.objects.all(), many=False)
    class Meta:
        model = MovieRecommendationWithinGroup
        fields = ['groupRecID', 'recID', 'groupID', 'createdAt', 'updatedAt']

class MovieRecMovieJoinedSerializer(serializers.Serializer):
    """
    Need to come back to this... meant to return a movie and a recommendation together
    """
    movie = serializers.StringRelatedField(many=True)

    class Meta:

        model = MovieRecommendation
        fields = ('__all__')


class CommentSerializer(serializers.HyperlinkedModelSerializer):
    postID = serializers.PrimaryKeyRelatedField(queryset=MovieRecommendationWithinGroup.objects.all(), many=False, required=False)
    commentUserID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = CommentOnGroupMovieRecommendation
        fields = ("commentID", "postID", "commentUserID", "commentBody", "commentResponseID", "createdAt", "updatedAt")

class EndorsementSerializer(serializers.HyperlinkedModelSerializer):
    recID = serializers.PrimaryKeyRelatedField(queryset=MovieRecommendation.objects.all(), many=False)
    endorserUserID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = EndorsementsOnMovieRecsInGroups
        fields = ("endorsementID", "endorserUserID", "recID", "createdAt")

class LikeSerializer(serializers.HyperlinkedModelSerializer):
    commentID = serializers.PrimaryKeyRelatedField(queryset=CommentOnGroupMovieRecommendation.objects.all(), many=False)
    userID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = LikesOnCommentsOnPosts
        fields = ("likeID", "userID", "commentID", "createdAt")

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = "__all__"

class GroupProfilePicturesSerializer(serializers.HyperlinkedModelSerializer):
    groupID = serializers.PrimaryKeyRelatedField(queryset=UserGroup.objects.all(), many=False)
    class Meta:
        model = GroupProfilePictures
        fields = ['S3Key', 'createdAt', 'groupID', 'groupPicID', 'fileName']

class UserProfilePicturesSerializer(serializers.HyperlinkedModelSerializer):
    userID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = UserProfilePictures
        fields = ['S3Key', 'createdAt', 'userID', 'userProPicID', 'fileName']

class NotificationSerializer(serializers.HyperlinkedModelSerializer):
    userID = serializers.PrimaryKeyRelatedField(read_only=True)
    receiverUserID = serializers.PrimaryKeyRelatedField(read_only=True)
    groupRecID = serializers.PrimaryKeyRelatedField(queryset=MovieRecommendationWithinGroup.objects.all(), many=False)
    commentID = serializers.PrimaryKeyRelatedField(queryset=CommentOnGroupMovieRecommendation.objects.all(), many=False)
    class Meta:
        model = UserNotifications
        fields = ['notificationID', 'userID', 'receiverUserID',
                  'notificationDescription', 'groupRecID', 'commentID', 'commentID', 'notificationSeen', 'createdAt']

class GroupChatPicturesSerializer(serializers.HyperlinkedModelSerializer):
    groupID = serializers.PrimaryKeyRelatedField(queryset=UserGroup.objects.all(), many=False, required=False)
    userID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = GroupChatPictures
        fields = ['groupchatPicID', 'fileName', 'S3Key', 'createdAt', 'groupID', 'userID']

class RankingsSerializer(serializers.HyperlinkedModelSerializer):
    creatorUserID = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = UserRankings
        fields = ['rankingsID', 'nameOfRankings', 'ordered', 'creatorUserID', 'createdAt', 'rankingsS3Key']

class RankingsItemSerializer(serializers.HyperlinkedModelSerializer):
    movieID = serializers.PrimaryKeyRelatedField(many=False, queryset=Movie.objects.all(), required=False)
    tvShowID = serializers.PrimaryKeyRelatedField(many=False, queryset=TVShow.objects.all(), required=False)
    rankingList = serializers.PrimaryKeyRelatedField(many=False, queryset=UserRankings.objects.all(), required=False)
    bookID = serializers.PrimaryKeyRelatedField(many=False, queryset=Book.objects.all(), required=False)
    podcastID = serializers.PrimaryKeyRelatedField(many=False, queryset=Podcast.objects.all(), required=False)
    episodeID = serializers.PrimaryKeyRelatedField(many=False, queryset=PodcastEpisode.objects.all(), required=False)

    class Meta:
        model = RankingsItems
        fields = ['rankingItemID', 'rankingList', 'movieID', 'tvShowID',
                  'bookID', 'podcastID', 'episodeID', 'rankingInList', 'rankingsDescription']
        validators = []

    def validate(self, attrs):
        """
        Overwritten in order to enforce either movieID or tvShowID being null, but not both

        May need to come back to this
        """
        return attrs

    def get_validation_exclusions(self):
        exclusions = super(RankingsItemSerializer, self).get_validation_exclusions()
        return exclusions + ['rankingList'] + ['movieID']

def validate_multimedia(attrs):
    """
    Ensures that a post contains a tvShowID, a movieID, or a bookID, but not several
    :param attrs: dict from serializer
    :return: raise error or return attrs
    """
    count_media_ids = 0
    print("attrs: " + str(attrs))
    for att in attrs:
        print("att: " + att)
        if att in ['bookID', 'movieID', 'tvShowID', 'podcastID', 'bookIDX', 'movieIDX', 'tvShowIDX', 'podcastIDX']:
            count_media_ids += 1
            if count_media_ids > 1:
                raise serializers.ValidationError("Can only have one of tvShowID, movieID, or bookID in request")
    if count_media_ids == 0:
        raise serializers.ValidationError("Need either one of movieID, tvShowID, or bookID in request")
    return attrs

class ExclusionSerializer(serializers.HyperlinkedModelSerializer):
    groupID = serializers.PrimaryKeyRelatedField(queryset=UserGroup.objects.all(), many=False, required=False)
    userID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())

    class Meta:
        model = OverallFeedExclusions
        fields = ['exclusionID', 'userID', 'groupID', 'createdAt']

class ReportSerializer(serializers.HyperlinkedModelSerializer):
    reporterUserID = serializers.PrimaryKeyRelatedField(read_only=True, default=serializers.CurrentUserDefault())
    groupRecID = serializers.PrimaryKeyRelatedField(queryset=MovieRecommendationWithinGroup.objects.all(), many=False, required=False)
    commentID = serializers.PrimaryKeyRelatedField(queryset=CommentOnGroupMovieRecommendation.objects.all(), many=False, required=False)

    class Meta:
        model = Report
        fields = ['reportID', 'commentID', 'groupRecID', 'reportComment', 'reportComment', 'reporterUserID', 'createdAt']

    def validate(self, attrs):
        """
        Overwritten in order to enforce either movieID or tvShowID being null, but not both
        """
        if 'commentID' in attrs and 'groupRecID' in attrs:
            raise serializers.ValidationError("Cannot have both groupRecID and commentID in a ranking item")
        elif 'commentID' not in attrs and 'groupRecID' not in attrs:
            raise serializers.ValidationError("Need either a groupRecID or a commentID in an item")
        return attrs

class PodcastSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Podcast
        fields = ['podcastID', 'spotifyPodcastID', 'description', 'spotifyURL', 'spotifyImageURL',
                  'adult', 'title', 'publisher']

class PodcastEpisodeSerializer(serializers.HyperlinkedModelSerializer):
    podcastID = serializers.PrimaryKeyRelatedField(queryset=Podcast.objects.all(), many=False, required=False)

    class Meta:
        model = PodcastEpisode
        fields = ['episodeID', 'audioPreviewURL', 'description', 'duration_ms', 'explicit', 'spotifyURL', 'spotifyID',
                  'spotifyImageURL', 'name', 'release_date', 'podcastID']


#TODO: implement this and other validators
def required(value):
    if value is None:
        raise serializers.ValidationError('This field is required')