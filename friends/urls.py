from django.urls import path
from . import views

urlpatterns = [
    path('', views.friend_list, name='friend_list'),
    path('add/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
    path('accept/<int:friendship_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('decline/<int:friendship_id>/', views.decline_friend_request, name='decline_friend_request'),
    path('remove/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('search/', views.search_users, name='search_users'),
    path('invite_friend/', views.invite_friend, name='invite_friend'),
    path('friend/<int:friend_id>/', views.friend_calendar_view, name='friend_calendar'),
]