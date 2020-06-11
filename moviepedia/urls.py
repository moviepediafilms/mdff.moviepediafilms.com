"""moviepedia URL Configuration

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
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView

urlpatterns = [
    re_path(
        r"^favicon\.ico$",
        RedirectView.as_view(url="/static/favicon.ico", permanent=True),
    ),
    re_path(
        r"^icon\.png$", RedirectView.as_view(url="/static/icon.png", permanent=True)
    ),
    re_path(
        r"^tile\.png$", RedirectView.as_view(url="/static/tile.png", permanent=True)
    ),
    re_path(
        r"^tile-wide\.png$",
        RedirectView.as_view(url="/static/tile-wide.png", permanent=True),
    ),
    re_path(
        r"^robots\.txt$",
        RedirectView.as_view(url="/static/robots.txt", permanent=True),
    ),
    re_path(
        r"^humans\.txt$",
        RedirectView.as_view(url="/static/humans.txt", permanent=True),
    ),
    re_path(
        r"^site\.webmanifest$",
        RedirectView.as_view(url="/static/site.webmanifest", permanent=True),
    ),
    re_path(
        r"^browserconfig\.xml$",
        RedirectView.as_view(url="/static/browserconfig.xml", permanent=True),
    ),
    path("admin/", admin.site.urls),
    path("", include("dff2020.urls")),
]
