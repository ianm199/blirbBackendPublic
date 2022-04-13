from .models import UserNotifications, MovieRecommendationWithinGroup, MovieRecommendation, CommentOnGroupMovieRecommendation
from rest_framework.request import Request


def create_comment_on_post_notification_revised(request: Request):
    """
    Creates a notification when a user comments on a post
    :param request: Django Request object
    :return: N/a notification object created
    """
    post_data = request.data
    comment_body = post_data['commentBody']
    if len(comment_body) > 200:
        comment_body = comment_body[0:200] + "..."
    post_id = post_data['postID']
    origin_user = request.user
    origin_group_rec = MovieRecommendationWithinGroup.objects.get(groupRecID=post_id)
    receiver_user = origin_group_rec.memberID
    if receiver_user.id == origin_user.id:
        return None
    content_title = str(origin_group_rec.recID)
    notification_desc_base = get_comment_notification_base(post_data)
    notification_description = notification_desc_base.format(origin_user.username, comment_body,
                                                             content_title, origin_group_rec.groupID.groupName)
    notification = UserNotifications(userID=origin_user, receiverUserID=receiver_user, groupRecID=origin_group_rec,
                                     notificationDescription=notification_description)
    notification.save()

def create_endorsement_notification_revised(request: Request):
    """
    Creates a notification when someone endorses one of your posts
    :param request: Django Request object
    :return: N/a notification object created
    """
    post_data = request.data
    rec_id = post_data['recID']
    origin_user = request.user
    origin_group_rec = MovieRecommendation.objects.get(movieRecID=rec_id)
    receiver_user = origin_group_rec.recommenderUserID
    if receiver_user.id == origin_user.id:
        return None
    content_title = str(origin_group_rec)
    notification_description = "@{0} endorsed your Blirb about {1}".format(receiver_user.username, content_title)
    notification = UserNotifications(userID=origin_user, receiverUserID=receiver_user,
                                     notificationDescription=notification_description)
    notification.save()

def create_like_on_comment_notification_revised(request: Request):
    """
        Create a notification for someone responding to a comment
        :param origin_group_rec_id: id of the rec object that it refers to
        :param comment_id: comment that is liked
        :param origin_user: user object that is commenting
        :return:
    """
    post_data = request.data
    comment_id = post_data['commentID']
    comment = CommentOnGroupMovieRecommendation.objects.get(commentID=comment_id)
    comment_body = comment.commentBody
    if len(comment_body) > 200:
        comment_body = comment_body[0:200] + "..."
    origin_user = request.user
    origin_group_rec = comment.postID
    receiver_user = origin_group_rec.memberID
    if origin_user == receiver_user:
        return None
    notification_description_base = '{0} liked your comment: {1} in a Blirb about {2} in {3}'
    content_title = str(origin_group_rec.recID)
    group_name = origin_group_rec.groupID.groupName
    notification_description = notification_description_base.format(origin_user.username, comment_body,
                                                                    content_title, group_name)
    notification = UserNotifications(userID=origin_user, receiverUserID=receiver_user,
                                     groupRecID=origin_group_rec, notificationDescription=notification_description)
    notification.save()

def get_comment_notification_base(request_data):
    """
    Gets the description for the notification helper method for comment notifications
    :param request_data: dictionary of data from a request
    :return: str description base
    """
    if 'commentResponseID' in request_data:
        base = '@{0} responded "{1}" to your comment in a Blirb about {2} in {3}'
    else:
        base = '@{0} commented on "{1}" on your Blirb about {2} in {3}'
    return base