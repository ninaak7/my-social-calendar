from django.urls import path
from . import views

urlpatterns = [
    path('', views.group_list, name='group_list'),
    path('add/', views.add_group, name='add_group'),
    path('<int:group_id>/', views.group_details, name='group_details'),
    path('<int:group_id>/edit/', views.edit_group, name='edit_group'),
    path('<int:group_id>/delete/', views.delete_group, name='delete_group'),
]