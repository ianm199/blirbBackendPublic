from rest_framework.pagination import LimitOffsetPagination
from rest_framework.utils.urls import replace_query_param
from rest_framework.pagination import _positive_int
from rest_framework.request import Request
from rest_framework.response import Response
from collections import OrderedDict
from django.conf import settings

class CustomLimitOffsetPagination(LimitOffsetPagination):
    """
    Custom pagination class that handles the case of endpoints that need to be paginated but may have more data coming
    in
    you must implement some form of get_next_max for this class to be functional
    """
    min_id_param = 'max_id'
    min_id = None
    default_limit = 20
    lambda_wrapper = settings.LAMBDA_WRAPPERS # Set to true while we are using dumb Lambda wrapper for the API

    def get_min_id(self, request: Request):
        """
        Parses the max_id paramter from the query parameters
        :param request:
        :return:
        """
        try:
            return _positive_int(request.query_params[self.min_id_param], )
        except (KeyError, ValueError):
            return 0

    def get_limit(self, request: Request):
        """
        Parses the max_id paramter from the query parameters
        :param request:
        :return:
        """
        try:
            return _positive_int(request.query_params[self.limit_query_param], )
        except (KeyError, ValueError):
            return self.default_limit

    def get_next_min(self, request: Request):
        """
        Gets the max ID currently in the pagination for the next link to use
        :param request:
        :return: int, or will raise error if not implemented
        """
        raise NotImplementedError

    def get_next_link(self):

        url = self.request.build_absolute_uri()
        url = replace_query_param(url, self.limit_query_param, self.limit)
        self.next_max = self.get_next_min(self.request)
        url = replace_query_param(url, self.min_id_param, self.next_max)
        split = url.split("8000")
        just_the_endpoint = split[-1]
        if self.lambda_wrapper:
            just_the_endpoint += "&queryparams=max_id,limit"
        return just_the_endpoint

    def get_paginated_response(self, data):
        self.count = self.get_count(data)
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('results', data)
        ]))