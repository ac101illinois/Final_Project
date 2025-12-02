from django.contrib import admin
from django.urls import path
from .views import (
    home_view,

)

app_name = "library"

urlpatterns = [
    path("home", home_view, name="home-view"),

]