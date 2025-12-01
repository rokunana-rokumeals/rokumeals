"""
MBG App URL Configuration
"""
from django.urls import path
from . import views

app_name = 'mbg_app'

urlpatterns = [
    # Web views
    path('', views.home, name='home'),
    path('recipe/<str:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('ingredient/<str:ingredient_id>/', views.ingredient_detail, name='ingredient_detail'),
    path('category/<str:category_id>/', views.category_detail, name='category_detail'),
    
    # API endpoints
    path('api/search/', views.search_api, name='search_api'),
    path('api/autocomplete/', views.autocomplete_api, name='autocomplete_api'),
    path('api/stats/', views.stats_api, name='stats_api'),
    path('api/recipe/<str:recipe_id>/', views.recipe_detail_api, name='recipe_detail_api'),
    path('api/ingredient/<str:ingredient_id>/', views.ingredient_detail_api, name='ingredient_detail_api'),
]