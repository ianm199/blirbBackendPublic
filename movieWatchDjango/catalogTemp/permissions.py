from rest_framework import permissions
from .models import *
from rest_framework.response import Response
from rest_framework import status
from .sql_queries import *
from .views import query_db


#TODO: Add owner type field to make this relevant
# Good example of custom permissions though
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.owner == request.user

def check_group_feed_permissions(request, *args, **kwargs):
    """
    Checks that a user requesting a group feed is actually in group
    :param request:
    :param args:
    :param kwargs:
    :return: Reponse(status.HTTP_400) if not in group
    """
    groupID = kwargs['groupID']
    groups = get_groups_user_in(request.user.id)['groupID']
    if groupID not in groups:
        return Response(status.HTTP_401_UNAUTHORIZED)



def get_groups_user_in(userID):
    group_query = listUserGroups.format(userID)
    group_headings = ['groupID', 'groupName', 'groupDesc', 'createdAt', 'updatedAt', 'creatorUserID']
    groups = query_db(group_query, group_headings)
    return groups
