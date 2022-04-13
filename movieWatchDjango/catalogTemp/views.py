# Create your views here.
import logging
from django.db.utils import IntegrityError
from rest_framework import permissions
from rest_framework import generics
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from rest_framework.request import Request
from typing import List
from .movieWatchAPI import *
from .sql_queries import *
import random
from drf_multiple_model.views import FlatMultipleModelAPIView
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from collections import OrderedDict
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.utils.urls import replace_query_param
from .custom_permissions import OwnerOfObjectPermission, check_group_feed_permissions
from .custom_pagination import CustomLimitOffsetPagination
from .view_utils import query_db, execute_query_nonatomic
from django.conf import settings
from django.db import models
from .notifications import create_comment_on_post_notification_revised, create_endorsement_notification_revised, create_like_on_comment_notification_revised
from .movieWatchAPI import NotificationSerializer
logger = logging.getLogger("info")
from .feeds import attach_user_profile_picture


@api_view()
def add_group_join_codes(request, *args, **kwargs):
    groups: List[UserGroup] = UserGroup.objects.all()
    for group in groups:
        group.generate_group_join_code()
    return Response({"statusCode":200, "Message": "Groups Updated"})

def get_user_info_by_id(user_id, select_parameters):
    #TODO: Refactor for generic application - also maybe just use django ORM?
    """
    Get username by ID
    :param user_id: user id
    :param select_parameters: list of str to select by
    :return: dict of user info with keys that match select_parameters
    """
    select_params_final = ""
    count = 0
    for param in select_parameters:
        if count > 0:
            select_params_final += "," + param
        else:
            select_params_final += param
        count += 1
    query = "select {0} from auth_user where id = {1}".format(select_params_final, user_id)
    headings = select_parameters
    try:
        user_info = query_db(query, headings)[0]
        return user_info
    except IndexError as e:
        raise ValueError("Username {0} does not exist in db".format(user_id))

@api_view()
def get_user_groupinfo(request: Request, *args, **kwargs):
    """
    Gets the information for all groups that a user is in
    :param request:
    :param args:
    :param kwargs:
    :return: A Response containing list of group dictionaries with all relevant information
    """
    user_id = request.user.id
    group_query = listUserGroups.format(user_id)
    group_headings = ['groupID', 'groupName', 'groupDesc', 'createdAt', 'updatedAt', 'creatorUserID', 'groupJoinCode']
    groups = query_db(group_query, group_headings)
    for group in groups:
        group_id = group['groupID']
        attach_group_pictures(group, group_id)
        attach_group_members(group, group_id)
    return Response(groups)

def attach_group_pictures(group_dict, group_id):
    """
    Helper method to attach picture keys to a dictionary
    :param group_dict: dictionary to be added to
    :param group_id: id to identify the group
    :return: N/A modify the group_dict with a posterS3Key that contains the key
    """
    picture_query = "select S3Key from catalogTemp_groupprofilepictures where groupID_id = {0} order by createdAt desc limit 1".format(group_id)
    headings = ['groupS3Key']
    try:
        picture = query_db(picture_query, headings)[0]
        group_dict['groupS3Key'] = picture['groupS3Key']
    except IndexError as e:
        group_dict['S3Key'] = ""


def attach_group_members(group_dict, group_id):
    """
    Helper method to attach a groupmembers list to a dictionary
    :param group_dict: dictionary to be modified
    :param group_id: group id
    :return: N/A dictionary is modified and adds a "members" list
    """
    users_query = list_group_members_query.format(group_id)
    user_headings = ['first_name', 'last_name', 'username', 'id']
    group_members = query_db(users_query, user_headings)
    for member in group_members:
        user_id = member['id']
        attach_user_profile_picture(member, user_id)
    group_dict['groupMembers'] = group_members




class GetGroupchatPhotos(APIView, CustomLimitOffsetPagination):


    def get_next_min(self, request: Request):
        return self.next_min

    def get_query(self, request):
        group_id = self.kwargs['groupID']
        self.offset = self.get_offset(request)
        self.limit = self.get_limit(request)
        self.max_id = self.get_min_id(request)
        if self.max_id == 0:
            base_query = get_groupchat_photos_lo
            photos_query = base_query.format(group_id, self.limit, self.offset)
        else:
            base_query = get_groupchat_photos_lo_max
            photos_query = base_query.format(group_id, self.max_id, self.limit, self.offset)
        return photos_query

    def get(self, request, *args, **kwargs):
        if not check_group_feed_permissions(request, self.kwargs['groupID']):
            return Response(status.HTTP_401_UNAUTHORIZED)
        query = self.get_query(request)
        headings = GroupChatPicturesSerializer.Meta.fields
        result = query_db(query, headings)
        try:
            self.next_min = result[-1]['groupchatPicID']
        except (IndexError, KeyError):
            self.next_min = 0
        return self.get_paginated_response(result)


def attach_feed_info(base_of_feed_dict, request: Request, include_group_info=False):
    """
    Attaches general feed information to group or overall feed base
    :param base_of_feed_dict: dict generate by feed view
    :return: modify dict to contain general feed info including media content, comments, endorsements, profile_pictures, etc
    """
    post_id = base_of_feed_dict['groupRecID']
    user_id = base_of_feed_dict['userID']
    rec_id = base_of_feed_dict['recID_id']
    attach_media_content(base_of_feed_dict, request)
    attach_endorsements_by_post(base_of_feed_dict, rec_id, user_id)
    attach_full_comments(base_of_feed_dict, post_id, include_group_info)
    attach_user_profile_picture(base_of_feed_dict, user_id)
    if include_group_info:
        attach_group_info(base_of_feed_dict, request)


def attach_group_info(base_of_feed_dict, request: Request):
    """
    Adds group info to a feed dict. Information will be stored in field "Groups_in:"
    :param base_of_feed_dict: dict that forms feed
    :param post_id: id of the post this corresponds to
    :return:
    """
    user_id_making_request = request.user.id
    post_user_id = base_of_feed_dict['userID']
    rec_id = base_of_feed_dict['recID_id']
    query = getCommonGroupsOnPost.format(user_id_making_request, post_user_id, rec_id)
    query_headings = ['groupID', 'groupName', 'groupDesc', 'createdAt', 'updatedAt', 'createrUserID', 'groupJoinCode']
    groups = query_db(query, query_headings)
    base_of_feed_dict['groups'] = groups


def attach_media_content(recommendation_dict, request:Request):
    """
    Helper method to attach media content such as tv tv and movie info to a dict containing relevant keys
    :param recommendation_dict:
    :return: N/A just adds field to dict with content info
    """
    if recommendation_dict['movieID'] is not None:
        movie_id = recommendation_dict['movieID']
        recommendation_dict['movieInfo'] = get_movie_info_by_id(movie_id)
        try:
            attach_media_interested(recommendation_dict, request, "movie", movie_id)
        except ValueError as e:
            logging.log(level=30, message="Error attaching interested: " + str(e))
    elif recommendation_dict['tvShowID'] is not None:
        tv_id = recommendation_dict['tvShowID']
        recommendation_dict['tvShowInfo'] = get_tv_info_by_id(tv_id)
        try:
            attach_media_interested(recommendation_dict, request, "tv", tv_id)
        except ValueError as e:
            logging.log(level=30, message="Error attaching interested: " + str(e))
    elif recommendation_dict['bookID'] is not None:
        book_id = recommendation_dict['bookID']
        recommendation_dict['bookInfo'] = get_book_info_by_id(book_id)
    elif recommendation_dict['podcastID'] is not None:
        podcast_id = recommendation_dict['podcastID']
        recommendation_dict['podcastInfo'] = get_podcast_info_by_id(podcast_id)
        if recommendation_dict['episodeID'] is not None:
            episode_id = recommendation_dict['episodeID']
            recommendation_dict['episodeInfo'] = get_episode_info_by_id(episode_id)

def attach_media_interested(recommendation_dict, request: Request, mode, id):
    """
    Helper method to attach "interested" to media. If the user has the media marked as "Interested" that will be a 1, otherwise 0
    :param recommendation_dict: dict that contains one of the supported media types movieID or tvShowID currently
    :param request: django request object
    :param mode: what type of media it is... "movie" if movie, "tv" if tv
    :param id:
    :return: n/a dict will be altered
    """
    user = request.user
    list_exists = True
    try:
        interested_list = UserRankings.objects.get(creatorUserID=user, nameOfRankings="Interested")
    except UserRankings.DoesNotExist:
        list_exists = False
    if mode == "movie" and list_exists:
        movie = Movie.objects.get(movieID=id)
        if RankingsItems.objects.filter(rankingList=interested_list, movieID=movie).exists():
            recommendation_dict['movieInfo']['interested'] = 1
        else:
            recommendation_dict['movieInfo']['interested'] = 0
    elif mode == "tv" and list_exists:
        tv_show = TVShow.objects.get(tvID=id)
        if RankingsItems.objects.filter(rankingList=interested_list, tvShowID=tv_show).exists():
            recommendation_dict['tvShowInfo']['interested'] = 1
        else:
            recommendation_dict['tvShowInfo']['interested'] = 0
    elif mode == "book" and list_exists:
        book = Book.objects.get(bookID=id)
        if RankingsItems.objects.filter(rankingList=interested_list, bookID=book).exists():
            recommendation_dict['bookInfo']['interested'] = 1
        else:
            recommendation_dict['bookInfo']['interested'] = 0
    elif mode == "movie" and not list_exists:
        recommendation_dict['movieInfo']['interested'] = 0
    elif mode == "tv" and not list_exists:
        recommendation_dict['tvShowInfo']['interested'] = 0
    elif mode == "book" and not list_exists:
        recommendation_dict['tvShowInfo']['interested'] = 0
    else:
        raise ValueError("Unsupported media type provided: " + str(mode))


def get_movie_info_by_id(id):
    """
    Returns a dict of info for a movie
    :param id: movie id
    :return: dictionary of movie info
    """
    query = "select movieTitle, description, runtime, genres, releaseDate, popularity, tagline, status, posterS3Key, imdb_id" \
            " from catalogTemp_movie where movieID = " + str(id)
    headings = ['movieTitle', 'description', 'runtime',
                  'genres', 'releaseDate', 'popularity', 'tagline', 'status', 'posterS3Key', 'imdb_id']
    movie_data = query_db(query, headings)
    imdb_link = 'https://www.imdb.com/title/' + str(movie_data[0]['imdb_id']) + "/"
    movie_data[0]['imdb_link'] = imdb_link
    return movie_data[0]

def get_tv_info_by_id(id):
    """
    Returns a dict of info for a tv show
    :param id: tvshow id
    :return: dictionary of tvshow info
    """
    query = "select showTitle, description, popularity, inProduction, posterS3Key" \
            " from catalogTemp_tvshow where tvID = " + str(id)
    headings = ['showTitle', 'description', 'popularity', 'inProduction', 'posterS3Key']
    movie_data = query_db(query, headings)
    return movie_data[0]

def get_book_info_by_id(id):
    """
    Returns a dict of info for a book
    :param id: id of the book
    :return: dict of book info
    """
    query = "select googleBookID, bookTitle, authors, publisher, description, pageCount, " \
            "categories, thumbnail, language, infoLink, previewLink, " \
            "canonicalVolumeLink from catalogTemp_book where bookID = " + str(id)
    query_headings = ['googleBookID', 'bookTitle', 'authors', 'publisher', 'description', 'pageCount', 'categories', 'thumbnail',
                      'language', 'infoLink', 'previewLink', 'canonicalVolumeLink']
    return query_db(query, query_headings)

def get_podcast_info_by_id(podcast_id):
    """
    Returns a dict of podcast info
    :param podcast_id:
    :return:
    """
    podcast = Podcast.objects.get(podcastID=podcast_id)
    serializer = PodcastSerializer(podcast)
    return serializer.data

def get_episode_info_by_id(episode_id):
    """
    Returns a dict of info related to a podcast
    """
    episode = PodcastEpisode.objects.get(episodeID=episode_id)
    serializer = PodcastEpisodeSerializer(episode)
    return serializer.data


class UserList(generics.ListAPIView):
    """
    List all users or create new user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)



class UserCreate(generics.CreateAPIView):
    """
    Create a user. Need to provide username and password
    """
    serializer_class = UserSerializer
    permission_classes = (AllowAny, )

    def create(self, request, *args, **kwargs):
        request_data = request.data
        required_fields = ['username', 'last_name', 'first_name', 'password', 'phoneNumber', 'email']
        signup_errors = []
        if settings.ALPHA_LAUNCH:
            required_fields.append("signUpCode")
        for field in required_fields:
            if field not in request_data:
                signup_errors.append(f"Missing required field: {field}")
        unique_fields = ['username', 'email']
        for field in unique_fields:
            data = {field:request_data[field]}
            if User.objects.filter(**data).exists():
                signup_errors.append(f"This {field} arlready in use. Must be unique")
        if UserDetails.objects.filter(phoneNumber=request_data['phoneNumber']).exists():
            signup_errors.append("Phone number already in use")
        if not SignUpCode.objects.filter(signUpCode=request_data['signUpCode']).exists():
            signup_errors.append(f"Sign up code {request_data['signUpCode']} invalid")
        if signup_errors:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"Errors": signup_errors})
        serializer = self.get_serializer(data=request_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()
        phone_number = int(self.request.data['phoneNumber'])
        user_id = serializer.data['id']
        user = User.objects.get(id=user_id)
        user_details = UserDetails(userID=user, phoneNumber=phone_number)
        self.create_interested_list(user)
        if 'signUpCode' in self.request.data:
            code = self.request.data['signUpCode']
            try:
                code_object = SignUpCode.objects.get(signUpCode=code)
                code_object.add_user_to_sign_up_groups(user)
            except models.ObjectDoesNotExist as e:
                self.permission_denied("Invalid signup code: " + str(code))
        else:
            if settings.ALPHA_LAUNCH:
                #return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error":"SignUpCode required"})
                self.permission_denied(request=self.request.authenticators, message="During alpha launch only users who sign up with a signUpCode are allowed")
        user_details.save()

    def create_interested_list(self, user):
        """
        Creates an interested list for the given user
        :param user: django user object
        :return: n/a creates an unorderd "interest" list for a the provided user
        """
        int_list = UserRankings(nameOfRankings="Interested", creatorUserID=user)
        int_list.save()


class AddToGroup(generics.CreateAPIView):
    """
    Add a member to a group. Need to provide userID and groupID
    """
    serializer_class = GroupMemberSerialzier
    permission_classes = (AllowAny, )

class UserGroupList(generics.ListAPIView):
    """
    Used to retrieve the list of groups a user is in
    """

    serializer_class = GroupSerializer
    def get_queryset(self):
        user = self.request.user.id
        groups = UserGroup.objects.raw(listUserGroups.format(user))
        return groups

class JoinGroupByCode(generics.CreateAPIView):
    """
    Allow a user to join group with JoinGroupCode
    """
    serializer_class = GroupMemberSerialzier
    queryset = GroupMembers.objects.all()

    def perform_create(self, serializer):
        data = self.request.data
        if 'joinGroupCode' not in data:
            return Response(status.HTTP_400_BAD_REQUEST("Missing parameter joinGroupCode"))
        if UserGroup.objects.filter(joinGroupCode=data['joinGroupCode']).exists():
            group_to_join: UserGroup = UserGroup.objects.get(joinGroupCode=data['joinGroupCode'])
            if group_to_join.user_in_group(self.request.user):
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error": "User already in group"})
            return Response(GroupMemberSerialzier(group_to_join.add_user_to_group(self.request.user)).data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error": "Invalid groupJoinCode"})

@api_view(["POST"])
def join_group_by_code(request, *args, **kwargs):
    data = request.data
    if 'joinGroupCode' not in data:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error":"Missing parameter joinGroupCode"})
    if UserGroup.objects.filter(groupJoinCode=data['joinGroupCode']).exists():
        group_to_join: UserGroup = UserGroup.objects.get(groupJoinCode=data['joinGroupCode'])
        if group_to_join.user_in_group(request.user):
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error": "User already in group"})
        return Response(GroupMemberSerialzier(group_to_join.add_user_to_group(request.user)).data)
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"Error": "Invalid groupJoinCode"})

@api_view(["GET"])
def ping(request: Request, *args, **kargs) -> Response:
    return Response(status=status.HTTP_200_OK, data={"Message":"Valid token!"})


class MovieDetail(generics.RetrieveAPIView):
    """
    Retrieve movie info
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    permission_classes = (IsAuthenticated,)


class TVDetail(generics.RetrieveAPIView):
    """
    Retrieve TV Info
    """
    queryset = TVShow.objects.all()
    serializer_class = TVSerializer
    permission_classes = (IsAuthenticated, )


class MovieRecsDetail(generics.ListAPIView):
    """
    Retrieve, update, create? movie recs
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    permission_classes = (IsAuthenticated,)

class CreateMovie(generics.CreateAPIView):
    """
    Create a movie
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer




class CreateMovieRec(generics.CreateAPIView):
    """
    Create a movie rec
    """
    queryset = MovieRecommendation.objects.all()
    serializer_class = MovieRecommendationSerializer

    permission_classes = (IsAuthenticated, )
    def perform_create(self, serializer):
        kwargs = {'recommenderUserID': self.request.user}
        serializer.save(**kwargs)



class GroupMembersList(generics.ListAPIView):
    """
    Get all users in a group
    """
    serializer_class = PublicUserSerializer

    permission_classes = (IsAuthenticated, )
    def get_queryset(self):
        users = User.objects.raw(listGroupMembers.format(self.request.GET.get('groupID')))
        return users


class GroupList(generics.ListCreateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        kwargs = {"createrUserID":self.request.user, "groupJoinCode":UserGroup.get_random_string(8)}
        serializer.save(**kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        group_id = serializer.data['groupID']
        creator_in_group = GroupMembers(userID=request.user, groupID=UserGroup.objects.get(groupID=group_id))
        creator_in_group.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class UserDetail(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = PublicUserSerializer

class UserDetailByUser(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = PublicUserSerializer
    lookup_field = 'username'

class GroupByID(generics.RetrieveAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupSerializer

class RemoveMemberFromGroup(generics.DestroyAPIView):
    serializer_class = GroupMemberSerialzier
    permission_classes = [IsAuthenticated, ]

    lookup_field = ['groupID', 'userID']
    def get_queryset(self):
        groupID = self.request.GET.get('groupID')
        userID = self.request.GET.get('userID')
        user = GroupMembers.objects.all().filter(groupID=groupID, userID=userID)
        return user

class RemoveMember(generics.DestroyAPIView):
    serializer_class = GroupMemberSerialzier
    #TODO: make group admin auth class
    permission_classes = [IsAuthenticated, ]

    lookup_field = ['groupID', 'userID']
    def get_object(self):
        groupID = self.kwargs['groupID']
        userID = self.kwargs['userID']
        user = GroupMembers.objects.all().filter(groupID=groupID).filter(userID=userID)
        return user

class CurrentUserDetail(generics.RetrieveUpdateAPIView):
    serializer_class = PublicUserSerializerCustom
    permission_classes = [IsAuthenticated, ]
    queryset = User.objects.all()

    def get_object(self):
        userID = self.request.user.id
        user = User.objects.get(id=userID)
        return user

class RemoveGroup(generics.DestroyAPIView):
    serializer_class = GroupSerializer
    queryset = UserGroup.objects.all()
    permission_classes = [IsAuthenticated, OwnerOfObjectPermission]

class UpdateGroup(generics.UpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (IsAuthenticated, )
    ALLOWED_UPDATE_FIELDS = ["groupName", "groupDesc"]
    def perform_update(self, serializer):
        """
        overwritten to not allow certain types of updates on a group
        """
        self.validate_group_permissions()
        self.validate_update_fields()
        serializer.save()

    def validate_update_fields(self):
        for data in self.request.data:
            if data not in self.ALLOWED_UPDATE_FIELDS:
                self.permission_denied(self.request, message="Invalid field to update: " + data)

    def validate_group_permissions(self):
        groupID = self.kwargs['pk']
        if not check_group_feed_permissions(self.request, groupID):
            self.permission_denied("Cannot update group if you are not a member of it")

class UpdateGroupAdmin(UpdateGroup):
    permission_classes = (IsAuthenticated, OwnerOfObjectPermission)
    ALLOWED_UPDATE_FIELDS = ["createrUserID"]

    def perform_update(self, serializer):
        """
        overwritten to not allow certain types of updates on a group
        """
        self.validate_group_permissions()
        self.validate_update_fields()
        user = User.objects.get(pk=self.request.data['createrUserID'])
        kwargs = {'createrUserID': user}
        serializer.save(**kwargs)


class AddMovieRecToGroup(generics.CreateAPIView):
    queryset = MovieRecommendationWithinGroup.objects.all()
    serializer_class = MovieRecInGroupSerializer
    permission_classes = (IsAuthenticated, )

    def perform_create(self, serializer):
        """
        Overwritten so that the user who create
        """
        data = self.request.data
        groupID = data['groupID']
        recID = data['recID']
        if not check_group_feed_permissions(self.request, groupID):
            self.permission_denied(self.request, message="test message 2")
        if not check_owner_of_rec(self.request, recID):
            self.permission_denied(self.request, message="test message")
        kwargs = {'memberID':self.request.user}
        serializer.save(**kwargs)

def check_owner_of_rec(request, recID):
    recommender = MovieRecommendation.objects.get(movieRecID=recID).recommenderUserID
    user = request.user
    return recommender == user

class RemoveMovieRecFromGroup(generics.DestroyAPIView):
    queryset = MovieRecommendationWithinGroup.objects.all()
    serializer_class = MovieRecInGroupSerializer
    permission_classes = (IsAuthenticated, OwnerOfObjectPermission)
    lookup_field = ['groupID', 'recID']
    def get_object(self):
        groupID = self.kwargs['groupID']
        recID = self.kwargs['recID']
        """
        if not check_owner_of_rec(self.request, recID):
            self.permission_denied(self.request)
        """
        movieRecInGroup = MovieRecommendationWithinGroup.objects.all().filter(groupID=groupID).filter(recID=recID)
        return movieRecInGroup

class GetMovieRec(generics.RetrieveAPIView):
    """
    Allows access to movie recs
    """
    queryset = MovieRecommendation.objects.all()
    serializer_class = MovieRecommendationSerializer
    permission_classes = (IsAuthenticated, )

class RemoveUpdateMovieRec(generics.RetrieveUpdateDestroyAPIView):
    """
    Allows recs to be destroyed and updated. Access should be restricted to the person who created them
    """
    queryset = MovieRecommendation.objects.all()
    serializer_class = MovieRecommendationSerializer
    permission_classes = (IsAuthenticated, OwnerOfObjectPermission)

    def check_object_permissions(self, request: Request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request)

        if request.method not in permissions.SAFE_METHODS:
            creator = obj.recommenderUserID
            user = request.user
            if creator != user:
                self.permission_denied(request)

class GetGroupsRecIn(generics.ListAPIView):
    """
    Gets all the group information
    """

    serializer_class = GroupSerializer
    def get_queryset(self):
        movieRecID = self.kwargs['movieRecID']
        groups = UserGroup.objects.raw(listGroupsMovieRecIn.format(movieRecID))
        return groups



class MovieRecsByGroup(generics.ListAPIView):
    """
    Get all movie recs in a group
    """
    serializer_class = MovieRecommendationSerializer
    permission_classes = (IsAuthenticated, )

    lookup_field = ['movieRecID']
    def get_queryset(self):
        groupID = self.kwargs['groupID']
        movieRecs = MovieRecommendation.objects.raw(listMovieRecsByGroups.format(groupID))
        return movieRecs

class MoviesList(generics.ListAPIView):
    """
    List all movies in the database
    """
    serializer_class = MovieSerializer
    queryset = Movie.objects.all()

class CreateCommentOnPost(generics.CreateAPIView):
    """
    To post a comment on a post
    """
    queryset = CommentOnGroupMovieRecommendation.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated, )

    def perform_create(self, serializer):
        """
        Overwritten so that the userID will be stored in a comment and a notification will get created
        :param serializer:
        :return:
        """
        data = self.request.data
        post_id = data['postID']
        group = MovieRecommendationWithinGroup.objects.get(groupRecID=post_id).groupID.groupID
        if not check_group_feed_permissions(self.request, group):
            self.permission_denied(self.request)
        kwargs = {'commentUserID': self.request.user}
        if 'commentResponseID' in self.request.data:
            immediate_parent_id = self.request.data['commentResponseID']
            immediate_parent_comment = CommentOnGroupMovieRecommendation.objects.get(commentID=immediate_parent_id)
            if immediate_parent_comment.commentParentID == 0:
                kwargs['commentParentID'] = immediate_parent_comment.commentID
            else:
                kwargs['commentParentID'] = immediate_parent_comment.commentParentID
            comment_depth = immediate_parent_comment.commentDepth + 1
        else:
            comment_depth = 0
        kwargs['commentDepth'] = comment_depth
        serializer.save(**kwargs)
        create_comment_on_post_notification_revised(self.request)



class UpdateCommentOnPost(generics.RetrieveUpdateDestroyAPIView):
    """
    To get update or delete comments
    """
    queryset = CommentOnGroupMovieRecommendation.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated, OwnerOfObjectPermission)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_comment = instance.delete_comment()
        serialized = self.serializer_class(deleted_comment)
        return Response(serialized.data)

    def check_object_permissions(self, request, obj):
        """
        Check if the request should be permitted for a given object.
        Raises an appropriate exception if the request is not permitted.
        """
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(request)

        if not check_comment_owner(self.request, self.kwargs['pk']):
            self.permission_denied(self.request)

def check_comment_owner(request: Request, commentID):
    """
    Checks owner of comment
    :param request: Django request object
    :param commentID: primary key that corresponds to the comment
    :return: true if the user is the owner of the comment false otherwise
    """
    user = request.user
    comment_user = CommentOnGroupMovieRecommendation.objects.get(pk=commentID).commentUserID
    return user == comment_user

class GetCommentsOnPost(generics.ListAPIView):
    """
    Gets the comments on posts
    """
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = ['postID']

    def get_queryset(self):
        postID = self.kwargs['postID']
        comments = CommentOnGroupMovieRecommendation.objects.all().filter(postID=postID)
        return comments

class GetUserWhoEndorsePost(generics.ListAPIView):
    """
    Gets the comments on posts
    """
    serializer_class = PublicUserSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = ['postID']

    def get_queryset(self):
        postID = self.kwargs['postID']
        users = User.objects.raw(getUsersWhoEndorsePosts.format(postID))
        return users

class CreateEndorsement(generics.CreateAPIView):
    """
    Allows a user to endorse a movie recommendation
    """
    serializer_class = EndorsementSerializer
    permission_classes = (IsAuthenticated, )

    def check_permissions(self, request):
        super().check_permissions(request)


    def perform_create(self, serializer):
        user = self.request.user
        kwargs = {'endorserUserID': user}
        serializer.save(**kwargs)
        create_endorsement_notification_revised(self.request)

class AddOrRemoveEndorsement(APIView):
    """
    This class will add a endorsement for a movie if there isn't already one and will remove it if there isn't one
    """
    def post(self, request, *args, **kwargs):
        post_data = self.request.data
        recID = post_data['recID']
        rec = MovieRecommendation.objects.get(movieRecID=recID)
        try:
            endorsement = EndorsementsOnMovieRecsInGroups.objects.get(recID=rec, endorserUserID=self.request.user)
            endorsement.delete()
            return Response(status.HTTP_200_OK)
        except models.ObjectDoesNotExist:
            endorsement = EndorsementsOnMovieRecsInGroups(recID=rec, endorserUserID=self.request.user)
            endorsement.save()
            serialized = EndorsementSerializer(endorsement)
            return Response(serialized.data)




class DeleteEndorsement(generics.DestroyAPIView):
    """
    Allows a user to remove an endorsement
    """
    serializer_class = EndorsementSerializer
    permission_classes = (IsAuthenticated, )
    queryset = EndorsementsOnMovieRecsInGroups.objects.all()

class LikeCommentOnPost(generics.CreateAPIView):
    """
    Allows a user to like a comment
    """
    serializer_class = LikeSerializer
    permission_classes = (IsAuthenticated, )
    queryset = LikesOnCommentsOnPosts.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        kwargs = {'userID': user}
        serializer.save(**kwargs)
        create_like_on_comment_notification_revised(self.request)

class DeleteLike(generics.DestroyAPIView):
    """
    Allows a user to remove a like from a post
    """
    serializer_class = LikeSerializer
    permission_classes = (IsAuthenticated,)
    queryset = LikesOnCommentsOnPosts.objects.all()

class GetUsersWhoLikeComment(generics.ListAPIView):
    """
    Gets a list of users who liked a comment
    """
    serializer_class = PublicUserSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        commentID = self.kwargs['commentID']
        users = User.objects.raw(getUsersWhoLikeAComment.format(commentID))
        return users

class FileUploadView(APIView):
    parser_classes = (FileUploadParser, )

    def post(self, request, *args, **kwargs):
        fileSerializer = FileSerializer(data=request.data)

        if fileSerializer.is_valid():
            fileSerializer.save()
            return Response(fileSerializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(fileSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetCurrenUserMovieRecs(generics.ListAPIView):
    """
    Get the movie recommendations for the current user
    """
    serializer_class = MovieRecommendationSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = MovieRecommendation.objects.all().filter(recommenderUserID=user)
        return queryset

class GetMovieRecsByUser(generics.ListAPIView):
    """
    Get the movie recommendations a given user
    """
    serializer_class = MovieRecommendationSerializer

    def get_queryset(self):
        user = self.kwargs['userID']
        queryset = MovieRecommendation.objects.all().filter(recommenderUserID=user)
        return queryset

class GetCurrentuserMovieRecsFeed(generics.ListAPIView):
    """
    Get a feed of movie recs for the currently logged in user
    """

    serializer_class = MovieRecommendationSerializer

    def get_queryset(self):
        userID = self.request.user.id
        queryset = MovieRecommendation.objects.raw(listMovieRecsByGroupsUserIn.format(userID))
        return queryset

class GetCommonGroups(generics.ListAPIView):
    """
    Get the common groups between the current user and a given user
    """
    serializer_class = GroupSerializer
    lookup_field = ["userID"]

    def get_queryset(self):
        userID = self.request.user.id
        otherUserID = self.kwargs['userID']
        queryset = UserGroup.objects.raw(getCommonGroups.format(userID, otherUserID))
        return queryset

class GetCommonMovieRecsFeed(generics.ListAPIView):
    """
    Get the common feed between two users, one of whom is the current user. This is what will be shown if you navigate
    to someones profile. Note there should also probably be be an option to specify recommendations as "public" and that
    should be counted in here
    """
    serializer_class = MovieRecommendationSerializer
    lookup_field = ['userID']

    def get_queryset(self):
        userID = self.request.user.id
        otherUserID = self.kwargs['userID']
        queryset = MovieRecommendation.objects.raw(getCommonFeed.format(userID, otherUserID))
        return queryset

class GetPostInfo(generics.RetrieveAPIView):
    serializer_class = MovieRecInGroupSerializer
    lookup_field = ['recID', 'groupID']
    queryset = MovieRecommendationWithinGroup.objects.all()

    def get_object(self):
        groupID = self.kwargs['groupID']
        recID = self.kwargs['recID']
        post = MovieRecommendationWithinGroup.objects.get(recID=recID, groupID=groupID)
        return post


class GetMovieRecsInGroups(generics.ListAPIView):
    serializer_class = MovieRecInGroupSerializer
    lookup_field = ['groupID']

    def get_queryset(self):
        groupID = self.kwargs['groupID']
        recs = MovieRecommendationWithinGroup.objects.all().filter(groupID=groupID)
        return recs

class GetMovieRecInGroup(generics.RetrieveAPIView):
    queryset = MovieRecommendationWithinGroup.objects.all()
    serializer_class = MovieRecInGroupSerializer

class DeleteCurrentUserEndorsement(generics.DestroyAPIView):
    queryset = EndorsementsOnMovieRecsInGroups.objects.all()
    serializer_class = EndorsementSerializer
    lookup_field = 'postID'

    def get_object(self):
        groupRecID = self.kwargs['postID']
        user = self.request.user
        endorsement = EndorsementsOnMovieRecsInGroups.objects.get(postID=groupRecID, endorserUserID=user)
        return endorsement

class DeleteCurrentuserLike(generics.DestroyAPIView):
    queryset = LikesOnCommentsOnPosts.objects.all()
    serializer_class = LikeSerializer
    lookup_field = 'commentID'

    def get_object(self):
        commentID = self.kwargs['commentID']
        user = self.request.user
        userLike = LikesOnCommentsOnPosts.objects.get(commentID=commentID, userID=user)
        return userLike

class MovieSearchByTitle(generics.ListAPIView):
    search_fields = ['movieTitle']
    filter_backends = (filters.SearchFilter, )
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

class MovieSearchByTitleTemp(generics.ListAPIView):
    serializer_class = MovieSerializer

    def get_queryset(self):
        searchTerm = self.kwargs['title']
        limit = int(self.kwargs['limit'])
        queryset = Movie.objects.filter(movieTitle__icontains=searchTerm).order_by('-popularity')[:limit]
        return queryset

class AddGroupProPic(generics.CreateAPIView):
    serializer_class = GroupProfilePicturesSerializer
    queryset = GroupProfilePictures.objects.all()

    def perform_create(self, serializer):
        """
        Overwritten to allow s3 key to be added
        :param serializer:
        :return:
        """
        userID = self.request.user.id
        s3key = "group-profile-pics/" + str(userID) + str(random.random())
        kwargs = {'S3Key': s3key}
        serializer.save(**kwargs)

class AddGroupChatPic(generics.CreateAPIView):
    serializer_class = GroupChatPicturesSerializer
    queryset = GroupChatPictures.objects.all()

    def perform_create(self, serializer):
        """
        Overwritten to allow s3 key to be added
        :param serializer:
        :return:
        """
        user = self.request.user
        group_id = self.kwargs['groupID']
        group = UserGroup.objects.get(pk=group_id)
        s3key = "group-chat-pictures/" + str(group_id) + "/" + str(random.random())
        kwargs = {'S3Key': s3key, 'userID':user, 'groupID':group}
        serializer.save(**kwargs)


class GetCurrentGroupProfilePicture(generics.ListAPIView):
    serializer_class = GroupProfilePicturesSerializer
    lookup_field = 'groupID'

    def get_queryset(self):
        groupID = self.kwargs['groupID']
        query = "select * from catalogTemp_groupprofilepictures where groupID_id = {0} order by createdAt desc limit 1".format(groupID)
        proPic = GroupProfilePictures.objects.raw(query)
        return proPic


@api_view(http_method_names=["POST"])
def upload_profile_pic(request: Request, *args, **kwargs):
    user = request.user
    try:
        existing_profile_picture: UserProfilePictures = UserProfilePictures.objects.get(userID=request.user)
        s3_key = "user-profile-pics/" + str(request.user.id) + str(random.random())
        existing_profile_picture.S3Key = s3_key
        existing_profile_picture.save()
    except models.ObjectDoesNotExist as e:
        s3_key = "user-profile-pics/" + str(request.user.id) + str(random.random())
        file_name = request.data['fileName']
        profile_picture = UserProfilePictures(userID=user, fileName=file_name, S3Key=s3_key)
        profile_picture.save()
    return Response(status=status.HTTP_200_OK, data={'S3Key': s3_key, 'userID': user.id})

class UploadCurrentUserProfilePicture(generics.CreateAPIView):
    serializer_class = UserProfilePicturesSerializer
    queryset = UserProfilePictures.objects.all()

    def perform_create(self, serializer):
        """
        Overwritten to add s3 key and user id
        :param serializer:
        :return:
        """
        user = self.request.user
        try:
            s3_key = UserProfilePictures.objects.get(userID=self.request.user).S3Key
        except models.ObjectDoesNotExist as e:
            s3_key = "user-profile-pics/" + str(self.request.user.id) + str(random.random())
        return Response(status=status.HTTP_200_OK, data={'S3Key':s3_key, 'userID':user})

class GetCurrentUserProfilePic(generics.ListAPIView):
    serializer_class = UserProfilePicturesSerializer
    queryset = UserProfilePictures.objects.all()

    def get_queryset(self):
        userID = self.request.user.id
        query = "select * from catalogTemp_userprofilepictures where userID_id = {0} order by createdAt desc limit 1".format(userID)
        proPic = UserProfilePictures.objects.raw(query)
        return proPic

class GetUserProfilePicture(generics.ListAPIView):
    serializer_class = UserProfilePicturesSerializer
    queryset = UserProfilePictures.objects.all()
    lookup_field = 'userID'

    def get_queryset(self):
        userID = self.kwargs['userID']
        query = "select * from catalogTemp_userprofilepictures where userID_id = {0} order by createdAt desc limit 1".format(userID)
        proPic = UserProfilePictures.objects.raw(query)
        return proPic


class TVSearchByTitle(generics.ListAPIView):
    """
    Allows TVShows to be queried by title
    """
    serializer_class = TVSerializer

    def get_queryset(self):
        """
        Overwritten to allow querying by title and limiting
        """
        searchTerm = self.kwargs['title']
        limit = int(self.kwargs['limit'])
        queryset = TVShow.objects.filter(showTitle__icontains=searchTerm).order_by('-popularity')[:limit]
        return queryset

from .feeds import attach_group_of_profile_pictures

class GetNotificationsCurrentUser(generics.ListAPIView, LimitOffsetPagination):
    """
    Gets notifications for current user
    """
    serializer_class = NotificationSerializer
    def get_queryset(self):
        """
        Overwriting to get data specific to user
        """
        self.limit = self.get_limit(self.request)
        self.offset = self.get_offset(self.request)
        user = self.request.user
        num_rows = len(UserNotifications.objects.all().filter(receiverUserID=user))
        end_window = min(num_rows, self.limit+self.offset)
        queryset = UserNotifications.objects.all().filter(receiverUserID=user).order_by('-createdAt')[self.offset:end_window]
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        list_users = []
        for notification in serializer.data:
            list_users.append(notification['userID'])
        final_data = attach_group_of_profile_pictures(serializer.data, list_users)
        return self.get_paginated_response(final_data)

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

    def get_next_link(self):

        url = self.request.build_absolute_uri()
        url = replace_query_param(url, self.limit_query_param, self.limit)

        offset = self.offset + self.limit
        return replace_query_param(url, self.offset_query_param, offset)

class MarkNotificationAsSeen(generics.UpdateAPIView):
    """
    Allows user
    """
    serializer_class = NotificationSerializer
    queryset = UserNotifications.objects.all()

    def perform_update(self, serializer):
        notification = UserNotifications.objects.get(pk=self.kwargs['pk'])
        notification.notificationSeen = False
        notification.save()

class MarkCurrentUserNotificationAsSeen(generics.UpdateAPIView):
    """
    Updates the users notfications who's making the request notifications to seen
    """
    serializer_class = NotificationSerializer
    queryset = UserNotifications.objects.all()

    def perform_update(self, serializer):
        notifications = UserNotifications.objects.get(receiverUseraID=self.request.user)
        notifications.notificationSeen = False
        notifications.save()

@api_view(http_method_names=["PATCH"])
def mark_user_notification_as_seen(request: Request, *args, **kwargs):
    """
    End point to
    :param requst:
    :param args:
    :param kwargs:
    :return:
    """
    try:
        user_id = request.user.id
        query = "UPDATE catalogTemp_usernotifications set notificationSeen = True where receiverUserID_id = " + str(user_id)
        execute_query_nonatomic(query)
    except Exception as e:
        #TODO: Implement logging for this kind of error / refactor query function
        return Response(status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(status.HTTP_200_OK)



class AddItemToInterested(generics.CreateAPIView):
    serializer_class = RankingsItemSerializer
    queryset = RankingsItems.objects.all()

    def user_has_interested_list(self, user):
        """
        Check if user already has interested list
        :param user: django user object
        :return: true if the user has a an interested list otherwise false
        """
        return UserRankings.objects.filter(creatorUserID=user, nameOfRankings="Interested").exists()

    def create_interested_list(self, user):
        """
        Creates an interested list for the given user
        :param user: django user object
        :return: n/a creates an unorderd "interest" list for a the provided user
        """
        int_list = UserRankings(nameOfRankings="Interested", creatorUserID=user)
        int_list.save()

    def perform_create(self, serializer):
        user = self.request.user
        if not self.user_has_interested_list(user):
            self.create_interested_list(user)
        interested_list = UserRankings.objects.get(creatorUserID=user, nameOfRankings="Interested")
        kwargs = {"rankingList":interested_list}
        serializer.save(**kwargs)

    def create(self, request, *args, **kwargs):
        """
        Overwritten so that if there is a duplicate entry, it will just be returned as HTTP 200
        """
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            return Response(status.HTTP_200_OK)


class RemoveFromInterested(generics.DestroyAPIView):
    serializer_class = RankingsSerializer
    queryset = RankingsItems.objects.all()

    def get_object(self):
        request_data = self.request.data
        user = self.request.user
        interested_list = UserRankings.objects.get(creatorUserID=user, nameOfRankings="Interested")
        if "movieID" in request_data:
            movie = Movie.objects.get(movieID=request_data['movieID'])
            rankings_object = RankingsItems.objects.get(rankingList=interested_list, movieID=movie)
        elif "tvShowID" in request_data:
            tv_show = TVShow.objects.get(tvID=request_data['tvShowID'])
            rankings_object = RankingsItems.objects.get(rankingList=interested_list, tvShowID=tv_show)
        elif "bookID" in request_data:
            book = Book.objects.get(bookID=request_data['bookID'])
            rankings_object = RankingsItems.objects.get(rankingsList=interested_list, bookID=book)
        else:
            self.permission_denied(self.request, message="Must attach a media type with request")
        return rankings_object



class CreateRankings(generics.CreateAPIView):
    serializer_class = RankingsSerializer
    queryset = UserRankings.objects.all()

    def perform_create(self, serializer):
        kwargs = {"creatorUserID":self.request.user}
        serializer.save(**kwargs)

@api_view(['POST'])
def add_item_to_list(request, *args, **kwargs):
    pass

class AddItemToList(generics.CreateAPIView):
    serializer_class = RankingsItemSerializer
    queryset = RankingsItems.objects.all()
    permission_classes = [IsAuthenticated, OwnerOfObjectPermission]
    PODCAST_KEYWORD = 'podcastIDX'
    PODCAST_EP_KEYWORD = 'episodeIDX'
    BOOK_KEYWORD= 'bookIDX'
    TMDB_MOVIE_KEYWORD='movieIDX'
    TMDB_TV_KEYWORD="tvShowIDX"

    def perform_create(self, serializer):
        post_data = self.request.data
        kwargs = {}
        if self.PODCAST_KEYWORD in post_data:
            podcast_id = post_data[self.PODCAST_KEYWORD]
            podcast = Podcast.get_or_create_object(podcast_id)
            kwargs['podcastID'] = podcast
            if self.PODCAST_EP_KEYWORD in post_data:
                episode_id = post_data[self.PODCAST_EP_KEYWORD]
                episode = PodcastEpisode.get_or_create_object(episode_id, podcast)
                kwargs['episodeID'] = episode

        elif self.BOOK_KEYWORD in post_data:
            book_id = post_data[self.BOOK_KEYWORD]
            book = Book.get_or_create_object(book_id)
            kwargs['bookID'] = book
        elif self.TMDB_MOVIE_KEYWORD in post_data:
            tmdb_id = post_data[self.TMDB_MOVIE_KEYWORD]
            movie = Movie.get_or_create_object(tmdb_id)
            kwargs['movieID'] = movie
        elif self.TMDB_TV_KEYWORD in post_data:
            tmdb_id = post_data[self.TMDB_TV_KEYWORD]
            show = TVShow.get_or_create_object(tmdb_id)
            kwargs['tvShowID'] = show
        else:
            acceptable_keys = ['movieID', 'tvShowID', 'bookID', 'podcastID', self.PODCAST_EP_KEYWORD,
                               self.PODCAST_KEYWORD, self.TMDB_TV_KEYWORD, self.TMDB_MOVIE_KEYWORD]
            if not any(x in post_data for x in acceptable_keys):
                self.permission_denied(message="Need to include of {} in request".format(acceptable_keys))
        serializer.save(**kwargs)

class GetUserLists(generics.ListAPIView):
    serializer_class = RankingsSerializer

    def get_queryset(self):
        queryset = UserRankings.objects.filter(creatorUserID=self.request.user)
        return queryset

class GetRankingstItems(APIView):

    def get(self, request, *args, **kwargs):
        rankings_list_id = self.kwargs['rankingsID']
        query_headings = ['rankingItemID', 'rankingInList', 'rankingsDescription','movieID', 'rankingList_id', 'tvShowID']
        query = get_base_of_rankings_list.format(rankings_list_id)
        rankings_items = query_db(query, query_headings)
        for ranking in rankings_items:
            attach_media_content(ranking, self.request)
        return Response(rankings_items)

class UpdateDeleteRankings(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RankingsSerializer
    queryset = UserRankings.objects.all()
    permission_classes = [IsAuthenticated, OwnerOfObjectPermission]

class UpdateDeleteRankingsItem(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RankingsItemSerializer
    queryset = RankingsItems.objects.all()
    permission_classes = [IsAuthenticated, OwnerOfObjectPermission]

class CurrentUserCreateExclusions(generics.CreateAPIView):
    serializer_class = ExclusionSerializer
    queryset = OverallFeedExclusions.objects.all()

    def perform_create(self, serializer):
        kwargs = {"userID":self.request.user}
        serializer.save(**kwargs)

class CurrentUserDeleteExclusion(generics.DestroyAPIView):
    serializer_class = ExclusionSerializer
    queryset = OverallFeedExclusions.objects.all()
    permission_classes = [IsAuthenticated, OwnerOfObjectPermission]

    def get_object(self):
        request_data = self.request.data
        user = self.request.user
        if "groupID" in request_data:
            group = UserGroup.objects.get(groupID=request_data['groupID'])
            return OverallFeedExclusions.objects.get(userID=user, groupID=group)
        elif "exclusionID" in request_data:
            return OverallFeedExclusions.objects.get(exclusionID=request_data['exclusionID'])
        else:
            self.permission_denied(message="Must to include either groupID or exclusionID with request")


class GetCurrentUserExclusions(generics.ListAPIView):
    serializer_class = ExclusionSerializer

    def get_queryset(self):
        user = self.request.user
        return OverallFeedExclusions.objects.filter(userID=user)

class CreateReport(generics.CreateAPIView):
    serializer_class = ReportSerializer
    queryset = Report.objects.all()

    def perform_create(self, serializer):
        request_data = self.request.data
        user = self.request.user
        kwargs = {"reporterUserID":user}
        if "commentID" in request_data and "groupRecID" in request_data:
            self.permission_denied(message="Can't have both 'commentID' and 'groupRecID' in POST")
        elif "commentID" in request_data:
            try:
                comment = CommentOnGroupMovieRecommendation.objects.get(commentID=request_data['commentID'])
                kwargs['commentID'] = comment
                serializer.save(**kwargs)
            except models.ObjectDoesNotExist as e:
                self.permission_denied("Invalid commentID")
        elif "groupRecID" in request_data:
            try:
                rec_object = MovieRecommendationWithinGroup.objects.get(groupRecID=request_data['groupRecID'])
                kwargs['groupRecID'] = rec_object
                serializer.save(**kwargs)
            except models.ObjectDoesNotExist as e:
                self.permission_denied("Invalid groupRecID")



@api_view(['DELETE'])
def leave_group(request, *args, **kwargs):
    try:
        group_member: GroupMembers = GroupMembers.objects.get(groupID=request.data['groupID'])
        group_member.delete()
        return Response({"statusCode":200, "message": "Succesfully left group"})
    except models.ObjectDoesNotExist as e:
        return Response({"message":"Invalid user groupID combo"}, status=status.HTTP_400_BAD_REQUEST)


class GetPodcastEpisodes(APIView):

    podcast_query_term = 'podcastID'
    limit_param = 'limit'
    offset_query_param = 'offset'
    DEFAULT_PAGE_LIMIT=50
    DEFAULT_OFFSET = 0
    base_endpoint = 'podcasts/episodes/'

    def get(self, request, *args, **kwargs):
        spotify_id = self.get_spotify_id()
        episode_data = Podcast.get_show_episodes_by_spotify_id(spotify_id, self.get_limit(), self.get_offset())
        episode_data['next'] = self.build_next()
        return Response(episode_data)

    def build_next(self):
        full_url = self.base_endpoint + '?{0}={1}&limit={2}&offset={3}'
        limit = self.get_limit()
        next_offset = int(limit) + int(self.get_offset())
        next_url = full_url.format(self.podcast_query_term, self.podcast_id, limit, next_offset)
        if settings.LAMBDA_WRAPPERS:
            next_url += "&queryparams=limit,offset"
        return next_url

    def get_spotify_id(self):
        try:
            self.podcast_id = self.request.query_params[self.podcast_query_term]
            return self.podcast_id
        except (KeyError, ValueError):
            self.permission_denied(self.request, message="Need to provide podcastID with request")

    def get_limit(self):
        try:
            self.limit = self.request.query_params[self.limit_param]
            return self.limit
        except (ValueError, KeyError):
            return self.DEFAULT_PAGE_LIMIT

    def get_offset(self):
        try:
            self.offset = self.request.query_params[self.offset_query_param]
            return self.offset
        except (ValueError, KeyError):
            return self.DEFAULT_OFFSET

class GetUserLists(APIView):

    def get(self, request, *args, **kwargs):
        if 'userID' in self.request.query_params:
            try:
                user = User.objects.get(pk=self.request.query_params['userID'])
            except models.ObjectDoesNotExist as e:
                self.request.permission_denied("invalid UserID")
        else:
            user = self.request.user
        rankings_data = self.get_lists_by_user(user)
        return Response(rankings_data)

    def get_lists_by_user(self, user):
        users_lists = UserRankings.objects.filter(creatorUserID=user)
        serializer = RankingsSerializer(users_lists, many=True)
        rankings_data = serializer.data
        for ranking_list in rankings_data:
            ranking_list_id = ranking_list['rankingsID']
            rankings = GetUserLists.get_rankings_items_by_id(ranking_list_id)
            for rank in rankings:
                attach_media_content(rank, self.request)
            ranking_list['items'] = rankings
        return rankings_data

    @staticmethod
    def get_rankings_items_by_id(id):
        query = "select rankingItemID, rankingInList, rankingsDescription, movieID_id, rankingList_id, tvShowID_id, " \
                "bookID_id, podcastID_id, episodeID_id from catalogTemp_rankingsitems where rankingList_id = {0}".format(id)
        headings = ['rankingItemID', 'rankingInList', 'rankingsDescription', 'movieID',
                    'rankingList', 'tvShowID','bookID', 'podcastID', 'episodeID']
        items = query_db(query, headings)
        return items


class SearchUserByUserName(APIView):
    """
    View to search users by User Name
    """

    def get(self, request: Request, *args, **kwargs):
        """
        Need to include ?username= with request
        """
        if 'username' in self.request.query_params:
            users = User.objects.filter(username__icontains=self.request.query_params['username'])
        elif 'phoneNumber' in self.request.query_params:
            users = []
            user_details = UserDetails.objects.filter(phoneNumber=int(self.request.query_params['phoneNumber']))
            for user in user_details:
                users.append(user.userID)
        else:
            self.permission_denied("Must include either phoneNumber or username as query param")
        users_data = PublicUserSerializer(users, many=True).data
        for user in users_data:
            attach_user_profile_picture(user, user['id'])
        return Response(users_data)
