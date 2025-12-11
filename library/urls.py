from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from .views import (
    home_view,
    mybooks_view,
    signup_view,
    bookdetail_view,
    stats_view,
    export_mybooks_csv,
    export_mybooks_json,

)

app_name = "library"

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home-view'), name='logout'),
    path('signup/', signup_view, name='signup'),
    path("home", home_view, name="home-view"),
    path("mybooks", mybooks_view, name="mybooks-view"),
    path("book/<int:book_id>", bookdetail_view, name="bookdetail-view"),
    path("stats", stats_view, name="stats-view"),
    path("stats/export/csv/", export_mybooks_csv, name="export-mybooks-csv"),
    path("stats/export/json/", export_mybooks_json, name="export-mybooks-json"),


]