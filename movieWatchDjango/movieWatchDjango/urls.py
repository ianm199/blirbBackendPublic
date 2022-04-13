"""movieWatchDjango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# Followed instructions here https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django/skeleton_website
# To set this up


urlpatterns = [
    path('admin/', admin.site.urls),
]

urlpatterns += [
    path('', include('catalogTemp.urls')),
]


urlpatterns += [
    path('', RedirectView.as_view(url='catalogTemp/', permanent=True)),
]

urlpatterns += [
    path('api-auth/', include('rest_framework.urls')),
]

#Add Django site authentication urls (for login, logout, password management)
urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)