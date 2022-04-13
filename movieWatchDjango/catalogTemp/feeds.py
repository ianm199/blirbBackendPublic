from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from .custom_pagination import CustomLimitOffsetPagination
from .sql_queries import get_over_feed_query_new, get_over_feed_query_new_no_min,\
    get_base_of_feed_query_lo, get_base_of_feed_query_lo_no_min, getCommonGroupsOnPost, get_users_who_endorse_post_query, \
    group_info_query, list_comments_users_group_together, list_comments_users_together
from .custom_permissions import check_group_feed_permissions
from .view_utils import query_db
from rest_framework import status
import logging
from .models import UserRankings, RankingsItems, Movie, Podcast, TVShow, PodcastEpisode, Book
from .movieWatchAPI import PodcastEpisodeSerializer, PodcastSerializer
from typing import List, Dict
from django.db.utils import ProgrammingError

class GetCommentsOnPost(APIView):
    """
    Gets the comments on posts
    """

    def get(self, request, *args, **kwargs):
        post_id = self.kwargs['postID']
        comments = format_subcomments(get_comments_and_users(post_id, False))
        return Response(status=status.HTTP_200_OK, data=comments)

class OverallFeed(APIView, CustomLimitOffsetPagination):
    """
    Gets the overall feed for user making the request, and implements limiting and offsetting pagination
    """
    include_group_info = True
    main_feed_headings = ["userID", "groupRecID", "createdAt", "updatedAt", "recID_id", "recommendationDesc",
                         "recommenderRating", "movieID", "tvShowID", "bookID",
                         "podcastID", "episodeID", "username", "first_name", "last_name"]

    def get_next_min(self, request: Request):
        return self.next_min

    def get(self, request, *args, **kwargs):
        recs_by_group = self.get_base_feed_data()
        min_group_rec_id = 0
        rec_ids = []
        index = 0
        result = []
        for rec in recs_by_group:
            group_rec_id = rec['groupRecID']
            rec_id = rec['recID_id']
            if rec_id in rec_ids:
                del recs_by_group[index:index+1]
                continue
            else:
                rec_ids.append(rec_id)
            attach_feed_info(rec, include_group_info=self.include_group_info, request=request)
            if min_group_rec_id == 0:
                min_group_rec_id = group_rec_id
            if group_rec_id < min_group_rec_id:
                min_group_rec_id = group_rec_id
            result.append(rec)
        self.next_min = min_group_rec_id
        return self.get_paginated_response(result)

    def get_base_feed_data(self):
        feed_query = self.get_query(self.request)
        feed_headings = self.main_feed_headings
        return query_db(feed_query, feed_headings)

    def get_query(self, request):
        user_id = request.user.id
        self.offset = self.get_offset(request)
        self.limit = self.get_limit(request)
        self.min_id = self.get_min_id(request)
        if self.min_id == 0:
            base_query = get_over_feed_query_new_no_min
            feed_query = base_query.format(user_id, user_id, self.limit)
        else:
            base_query = get_over_feed_query_new
            feed_query = base_query.format(self.min_id, user_id, user_id, self.limit)
        print("Feed query:" + feed_query)
        return feed_query

class GroupFeed(OverallFeed):
    """
    Class to get overall feed
    """
    include_group_info = False

    def get_query(self, request):
        groupID = self.kwargs['groupID']
        if not check_group_feed_permissions(request, groupID):
            raise AssertionError("User not in group")
        self.limit = self.get_limit(request)
        self.offset = self.get_offset(request)
        self.min_id = self.get_min_id(request)
        if self.min_id == 0:
            group_query = get_base_of_feed_query_lo_no_min.format(groupID, self.limit)
        else:
            group_query = get_base_of_feed_query_lo.format(groupID, self.min_id, self.limit)
        return group_query

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except AssertionError as e:
            return Response(status.HTTP_401_UNAUTHORIZED)


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



def attach_user_profile_picture(dict, user_id):
    """
    Helper method to attach profile pictures to dicts by user id
    :param dict: dictionary to append to
    :param user_id: user di to query by
    :return: n/a will modify to dict to have a key "S3Key" and a picture link
    """
    profile_pic_query = "select S3Key from catalogTemp_userprofilepictures where " \
                         "userID_id = {0} order by createdAt desc limit 1".format(user_id)
    headings = ['S3Key']
    try:
        profile_picture = query_db(profile_pic_query, headings)[0]
        dict['S3Key'] = profile_picture['S3Key']
    except IndexError as e:
        dict['S3Key'] = ""


def attach_group_of_profile_pictures(list_users: List[dict], list_user_ids: List[dict]) -> list:
    just_user_ids_no_brackets = str(list_user_ids).strip("[").strip("]")
    bulk_query = "select S3Key, userID_id from catalogTemp_userprofilepictures where " \
                 "userID_id in ({0}) group by userID_id order by createdAt limit 1".format(just_user_ids_no_brackets)
    print("problematic query: " + str(bulk_query))
    try:
        results = query_db(bulk_query, headings=['S3Key', 'userID'])
    except ProgrammingError as e:
        return list_users
    results_dict = {}
    for result in results:
        user_id = result['userID']
        results_dict[result['userID']] = result
    for user in list_users:
        user = attach_key(user, results_dict)
    return list_users

def attach_key(user, results_dict):
    try:
        user_id = user['userID']
        s3_key = results_dict[user_id]['S3Key']
        user['S3Key'] = s3_key
    except KeyError as e:
        pass
    return user


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

def attach_endorsements_by_post(recommendation_dict, rec_id, user_id):
    """
    Helper method to attach endorsements that are related to a post in a group. Will throw KeyError if recID_id n
    :param recommendation_dict: dict that will serve as a base
    :param rec_id: id that corresponds to the rec_id within the group
    :return: N/A endorsements added as a list of dict of users under key 'endorsements'
    """
    endorsements_query = get_users_who_endorse_post_query.format(rec_id, user_id)
    headings = ["first_name", "last_name","username"]
    endorsements_users = query_db(endorsements_query, headings)
    recommendation_dict['endorsements'] = endorsements_users


def attach_full_comments(recommendation_dict, post_id, include_group_info=False):
    """
    Attaches comment threads with user info and likes attached to a recommendation_dict
    :param recommendation_dict: a dict to be appended to
    :param post_id: id that corresponds to the recommendation within the group
    :return: N/A will add field "comments" with values as a list of dictionary that represents comments
    """
    if include_group_info:
        recommendation_dict['comments'] = []
        rec_id = recommendation_dict['recID_id']
        query = group_info_query.format(rec_id)
        headings = ["post_id", "group_id", "groupName", "S3Key"]
        post_id_and_groups = query_db(query, headings)
        for post in post_id_and_groups:
            post_id = post['post_id']
            post['comments'] = format_subcomments(get_comments_and_users(post_id))
            recommendation_dict['comments'].append(post)
    else:
        recommendation_dict['comments'] = format_subcomments(get_comments_and_users(post_id, include_group_info))


def attach_full_comments_v2(recommendation_dict, post_id):
    """
    Reworked version of attaching full comments. This should be able to attach all comments in one db query
    :param recommendation_dict: dict of recommendations from feed
    :post_id: the group rec id the post corresponds to
    """
    query = "select commentID, commentBody, commentResponseID, createdAt, updatedAt, commentUserID_id, postID_id," \
            " commentParentID, commentDepth from catalogTemp_commentongroupmovierecommendation where postID_id = {} order by " \
            "commentParentID".format(post_id)
    headings = ["commentID,", "commentBody", "commentResponseID", "createdAt", "updatedAt", "commentUserID_id",
                "postID_id", "commentParentID", "commentDepth"]
    comments_on_post = query_db()
    pass


def format_subcomments(comments_dict):
    """
    Formats a dict of comments so that subcomments will appear nested
    :param comments_dict: dict of comments
    :return: list of comments dicts
    """
    response_comments_dict = {}
    parent_comments = []
    for comment in comments_dict:
        """
        Based on logic in DB that commentResponseID 0 means its a parent commment
        """
        comment_response_id = comment['commentResponseID']
        if comment_response_id == 0:
            parent_comments.append(comment)
        else:
            if comment_response_id not in response_comments_dict:
                response_comments_dict[comment_response_id] = [comment]
            else:
                response_comments_dict[comment_response_id].append(comment)

    for parent_comment in parent_comments:
        add_all_comments_to_comment(parent_comment, response_comments_dict)


    return parent_comments

# Want algorithm to add all comments that are linked to it, and then recursively search for linked comments

def add_all_comments_to_comment(parent_comment, responses_dict):
    parent_comment['comments'] = []
    comment_id = parent_comment['commentID']
    if comment_id in responses_dict:
        comments = responses_dict[comment_id]
        for response in comments:
            response_response_id = response['commentID']
            if response_response_id not in responses_dict:
                parent_comment['comments'].append(response)
            else:
                add_all_comments_to_comment(response, responses_dict)
                parent_comment['comments'].append(response)
                del responses_dict[response_response_id]

def get_comments_and_users(post_id, include_group_info=False):
    """
    Get comments and users together
    :param: post_id: groupRecID that corresponds to the group being
    :return: list of dictionaries that contains both comment info and user info
    """
    data = get_comments_by_postID_with_user_info_help(post_id, include_group_info)
    for data_dict in data:
        commentID = data_dict['commentID']
        likes_data = get_likes_on_comment(commentID)
        data_dict['likes'] = likes_data
    return data

def get_likes_on_comment(commentID):
    """
    get likes on a comment by commentID
    :param commentID: int comment ID for desired comments
    :return: dictionary of users
    """
    query = "select username, first_name, last_name from auth_user where id" \
            " in (select userID_id from catalogTemp_likesoncommentsonposts where commentID_id = {0})".format(commentID)
    headings = ["username", "first_name", "last_name"]
    users_dict = query_db(query, headings)
    return users_dict


def get_comments_by_postID_with_user_info_help(post_id, include_group_info=False):
    """
    get comments by postID with user info
    :param post_id: groupRecID that corresponds to the recommendation
    :param includ_group_info: Bool if true will include group info with all comments
    :return: list of dictionaries with comment and user ID
    """
    if include_group_info:
        comment_headers = ["commentID", "postID", "commentUserID", "commentBody", "commentResponseID", "createdAt",
                       "updatedAt", "first_name", "last_name", "username", "group_ID", "groupName", "groupDesc"]
        comment_query = list_comments_users_group_together.format(post_id)
    else:
        comment_headers = ["commentID", "postID", "commentUserID", "commentBody", "commentResponseID", "createdAt",
                           "updatedAt", "first_name", "last_name", "username", "group_ID"]
        comment_query = list_comments_users_together.format(post_id)
    result = query_db(comment_query, comment_headers)
    return result

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