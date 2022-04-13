from rest_framework import permissions
from .models import GroupMembers, UserGroup
from rest_framework.request import Request

class OwnerOfObjectPermission(permissions.BasePermission):
    """
    Custom permissions class that only allows access if the user making the request is the owner of the object
    """

    def has_object_permission(self, request: Request, view, obj):
        if callable(obj.get_owner):
            return request.user == obj.get_owner()
        else:
            return False

class InGroupPermission(permissions.BasePermission):
    """
    Checks if user is in the group that owns the object
    """

    @staticmethod
    def get_groups_for_user(user):
        return GroupMembers.objects.filter(userID=user).groupID

    def has_object_permission(self, request, view, obj):
        user = request.user
        user_groups = InGroupPermission.get_groups_for_user(user)
        if callable(obj.get_group):
            obj_group = obj.get_group()
        else:
            return False
        return obj_group in user_groups

def check_group_feed_permissions(request: Request, groupID):
    """
    Checks that a user requesting a group feed is actually in group. Returns true if in group, false otherwise
    :param request: request that is being made
    :param groupID: groupID to check
    :return: Reponse(status.HTTP_400) if not in group
    """
    user = request.user
    group = UserGroup.objects.get(groupID=groupID)
    return GroupMembers.objects.filter(groupID=group, userID=user).exists()
