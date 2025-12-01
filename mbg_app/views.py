"""
MBG Knowledge Graph Views
Views untuk search functionality dan API endpoints
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from neomodel import db
import json

from .models import Recipe, Ingredient, Category

def home(request):
    """Homepage dengan search interface"""
    context = {
        'total_recipes': len(Recipe.nodes.all()),
        'total_ingredients': len(Ingredient.nodes.all()),
        'total_categories': len(Category.nodes.all()),
    }
    return render(request, 'mbg_app/home.html', context)

@csrf_exempt
def search_api(request):
    """
    API endpoint untuk searching
    Supports: /api/search/?q=query&type=recipe|ingredient|category&limit=20
    """
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        search_type = request.GET.get('type', 'all').lower()
        limit = int(request.GET.get('limit', 20))
        
        if not query:
            return JsonResponse({
                'status': 'error',
                'message': 'Query parameter is required',
                'data': []
            })
        
        results = []
        
        try:
            if search_type == 'all' or search_type == 'recipe':
                recipes = Recipe.search_by_name(query, limit)
                for recipe in recipes:
                    results.append({
                        'type': 'recipe',
                        'id': recipe.recipe_id,
                        'title': recipe.title,
                        'rating': recipe.rating,
                        'calories': recipe.calories,
                        'description': recipe.description[:200] + '...' if recipe.description and len(recipe.description) > 200 else recipe.description,
                        'ingredient_count': recipe.ingredient_count,
                        'categories': recipe.categories_list
                    })
            
            if search_type == 'all' or search_type == 'ingredient':
                ingredients = Ingredient.search_by_name(query, limit)
                for ingredient in ingredients:
                    results.append({
                        'type': 'ingredient',
                        'id': ingredient.ingredient_id,
                        'name': ingredient.name,
                        'category': ingredient.category,
                        'calories_per_100g': ingredient.calories_per_100g,
                        'recipe_count': ingredient.recipe_count
                    })
            
            if search_type == 'all' or search_type == 'category':
                categories = Category.search_by_name(query, limit)
                for category in categories:
                    results.append({
                        'type': 'category',
                        'id': category.category_id,
                        'name': category.name,
                        'category_type': category.type,
                        'item_count': category.item_count
                    })
            
            return JsonResponse({
                'status': 'success',
                'message': f'Found {len(results)} results for "{query}"',
                'data': results,
                'total': len(results)
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Search error: {str(e)}',
                'data': []
            })
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})

def recipe_detail_api(request, recipe_id):
    """API endpoint untuk detail recipe"""
    try:
        recipe = Recipe.nodes.get(recipe_id=recipe_id)
        
        # Get related ingredients
        ingredients = []
        for ingredient in recipe.contains.all():
            ingredients.append({
                'id': ingredient.ingredient_id,
                'name': ingredient.name,
                'calories_per_100g': ingredient.calories_per_100g,
                'category': ingredient.category
            })
        
        # Get categories
        categories = []
        for category in recipe.belongs_to.all():
            categories.append({
                'id': category.category_id,
                'name': category.name,
                'type': category.type
            })
        
        data = {
            'id': recipe.recipe_id,
            'title': recipe.title,
            'rating': recipe.rating,
            'calories': recipe.calories,
            'protein': recipe.protein,
            'fat': recipe.fat,
            'sodium': recipe.sodium,
            'description': recipe.description,
            'directions': recipe.directions,
            'ingredients': ingredients,
            'categories': categories,
            'ingredient_count': len(ingredients)
        }
        
        return JsonResponse({
            'status': 'success',
            'data': data
        })
        
    except Recipe.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Recipe not found'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def ingredient_detail_api(request, ingredient_id):
    """API endpoint untuk detail ingredient"""
    try:
        ingredient = Ingredient.nodes.get(ingredient_id=ingredient_id)
        
        # Get recipes yang menggunakan ingredient ini
        recipes = []
        for recipe in ingredient.used_in.all():
            recipes.append({
                'id': recipe.recipe_id,
                'title': recipe.title,
                'rating': recipe.rating,
                'calories': recipe.calories
            })
        
        data = {
            'id': ingredient.ingredient_id,
            'name': ingredient.name,
            'category': ingredient.category,
            'calories_per_100g': ingredient.calories_per_100g,
            'kj_per_100g': ingredient.kj_per_100g,
            'recipes': recipes,
            'recipe_count': len(recipes)
        }
        
        return JsonResponse({
            'status': 'success',
            'data': data
        })
        
    except Ingredient.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Ingredient not found'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def autocomplete_api(request):
    """
    API untuk autocomplete search suggestions
    Returns: top 10 suggestions based on query
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    try:
        # Get recipe suggestions
        recipes = Recipe.search_by_name(query, 5)
        for recipe in recipes:
            suggestions.append({
                'text': recipe.title,
                'type': 'recipe',
                'id': recipe.recipe_id
            })
        
        # Get ingredient suggestions
        ingredients = Ingredient.search_by_name(query, 5)
        for ingredient in ingredients:
            suggestions.append({
                'text': ingredient.name,
                'type': 'ingredient',
                'id': ingredient.ingredient_id
            })
        
        return JsonResponse({'suggestions': suggestions})
        
    except Exception as e:
        return JsonResponse({
            'suggestions': [],
            'error': str(e)
        })

def stats_api(request):
    """API endpoint untuk statistik database"""
    try:
        stats = {
            'total_recipes': len(Recipe.nodes.all()),
            'total_ingredients': len(Ingredient.nodes.all()),
            'total_categories': len(Category.nodes.all()),
            'top_rated_recipes': [],
            'popular_ingredients': []
        }
        
        # Top rated recipes
        top_recipes = Recipe.nodes.filter(rating__gt=0).order_by('-rating')[:5]
        for recipe in top_recipes:
            stats['top_rated_recipes'].append({
                'title': recipe.title,
                'rating': recipe.rating,
                'id': recipe.recipe_id
            })
        
        return JsonResponse({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })


def recipe_detail(request, recipe_id):
    """Recipe detail page"""
    try:
        recipe = Recipe.nodes.get(recipe_id=recipe_id)
        
        # Get related ingredients
        ingredients = []
        for ingredient in recipe.contains.all():
            ingredients.append({
                'id': ingredient.ingredient_id,
                'name': ingredient.name,
                'category': ingredient.category,
                'calories_per_100g': ingredient.calories_per_100g,
            })
        
        # Get related categories
        categories = []
        for category in recipe.belongs_to.all():
            categories.append({
                'id': category.category_id,
                'name': category.name,
                'type': category.type,
            })
        
        context = {
            'item': recipe,
            'ingredients': ingredients,
            'categories': categories,
            'related_items': ingredients + categories,
            'type': 'recipe',
            'title': recipe.title,
        }
        
        return render(request, 'mbg_app/detail.html', context)
        
    except Recipe.DoesNotExist:
        context = {
            'error': 'Recipe not found',
            'message': f'Recipe with ID "{recipe_id}" does not exist.'
        }
        return render(request, 'mbg_app/404.html', context, status=404)


def ingredient_detail(request, ingredient_id):
    """Ingredient detail page"""
    try:
        ingredient = Ingredient.nodes.get(ingredient_id=ingredient_id)
        
        # Get recipes that contain this ingredient
        recipes = []
        for recipe in ingredient.used_in.all():
            recipes.append({
                'id': recipe.recipe_id,
                'title': recipe.title,
                'rating': recipe.rating,
                'calories': recipe.calories,
            })
        
        # Get related categories (try both direct classification and category from name)
        categories = []
        try:
            for category in ingredient.classified_as.all():
                categories.append({
                    'id': category.category_id,
                    'name': category.name,
                    'type': category.type,
                })
        except:
            # If no direct relationship, try to find category by name
            try:
                category_nodes = Category.nodes.filter(name__icontains=ingredient.category)
                for cat in category_nodes[:3]:
                    categories.append({
                        'id': cat.category_id,
                        'name': cat.name,
                        'type': cat.type,
                    })
            except:
                pass
        
        context = {
            'item': ingredient,
            'recipes': recipes[:12],  # Limit to 12 recipes
            'categories': categories,
            'related_items': recipes[:8] + categories,
            'type': 'ingredient',
            'title': ingredient.name,
        }
        
        return render(request, 'mbg_app/detail.html', context)
        
    except Ingredient.DoesNotExist:
        context = {
            'error': 'Ingredient not found',
            'message': f'Ingredient with ID "{ingredient_id}" does not exist.'
        }
        return render(request, 'mbg_app/404.html', context, status=404)


def category_detail(request, category_id):
    """Category detail page"""
    try:
        category = Category.nodes.get(category_id=category_id)
        
        # Get recipes in this category using Cypher query
        recipes = []
        try:
            # Try direct relationship first
            for recipe in category.recipe_set.all():
                recipes.append({
                    'id': recipe.recipe_id,
                    'title': recipe.title,
                    'rating': recipe.rating,
                    'calories': recipe.calories,
                })
        except:
            # If no direct relationship, use Cypher query
            from neomodel import db
            results, meta = db.cypher_query(
                "MATCH (c:Category {category_id: $category_id})<-[:BELONGS_TO]-(r:Recipe) "
                "RETURN r.recipe_id as recipe_id, r.title as title, r.rating as rating, r.calories as calories "
                "LIMIT 12",
                {'category_id': category_id}
            )
            for result in results:
                recipes.append({
                    'id': result[0],
                    'title': result[1], 
                    'rating': result[2] or 0,
                    'calories': result[3] or 0,
                })
        
        # Get ingredients in this category
        ingredients = []
        try:
            for ingredient in category.ingredient_set.all():
                ingredients.append({
                    'id': ingredient.ingredient_id,
                    'name': ingredient.name,
                    'calories_per_100g': ingredient.calories_per_100g,
                })
        except:
            # Use Cypher query for ingredients
            from neomodel import db
            results, meta = db.cypher_query(
                "MATCH (c:Category {category_id: $category_id})<-[:CLASSIFIED_AS]-(i:Ingredient) "
                "RETURN i.ingredient_id as ingredient_id, i.name as name, i.calories_per_100g as calories "
                "LIMIT 12",
                {'category_id': category_id}
            )
            for result in results:
                ingredients.append({
                    'id': result[0],
                    'name': result[1],
                    'calories_per_100g': result[2] or 0,
                })
        
        context = {
            'item': category,
            'recipes': recipes[:12],  # Limit to 12 recipes
            'ingredients': ingredients[:12],  # Limit to 12 ingredients
            'related_items': recipes[:6] + ingredients[:6],
            'type': 'category',
            'title': category.name,
        }
        
        return render(request, 'mbg_app/detail.html', context)
        
    except Category.DoesNotExist:
        context = {
            'error': 'Category not found',
            'message': f'Category with ID "{category_id}" does not exist.'
        }
        return render(request, 'mbg_app/404.html', context, status=404)
