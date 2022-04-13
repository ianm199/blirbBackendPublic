from django.contrib import admin
from .models import *
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin



admin.site.register(UserGroup)
admin.site.register(MovieRecommendation)
admin.site.register(UserProfile)
admin.site.register(Movie)




