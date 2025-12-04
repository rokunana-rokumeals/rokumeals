from django.urls import path
from . import views

app_name = 'query_field'

urlpatterns = [
    path('', views.query_console, name='query_console'),
    path('execute/', views.execute_query, name='execute_query'),
]
