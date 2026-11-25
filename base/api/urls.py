from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('', views.getRoutes, name='root'),
    path('rooms/', views.getRooms, name='room-list'),
    path('rooms/<str:pk>/', views.getRoom, name='room-detail'),

]
