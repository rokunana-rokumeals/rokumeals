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
import logging

from .models import Recipe, Ingredient, Category

logger = logging.getLogger(__name__)

def home(request):
    """Homepage dengan search interface"""
    # Use efficient Cypher queries instead of nodes.all()
    recipe_count, _ = db.cypher_query("MATCH (r:Recipe) RETURN count(r) as count")
    ingredient_count, _ = db.cypher_query("MATCH (i:Ingredient) RETURN count(i) as count")
    category_count, _ = db.cypher_query("MATCH (c:Category) RETURN count(c) as count")
    
    context = {
        'total_recipes': recipe_count[0][0],
        'total_ingredients': ingredient_count[0][0],
        'total_categories': category_count[0][0],
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


@require_http_methods(["POST"])
@csrf_exempt
def enrich_ingredient(request, ingredient_id):
    """
    Enrich ingredient with Wikidata data on-demand
    """
    try:
        # Get ingredient
        ingredient = Ingredient.nodes.get(ingredient_id=ingredient_id)
        
        # Check if already enriched recently (to avoid duplicate calls)
        if hasattr(ingredient, 'wikidata_entity') and ingredient.wikidata_entity:
            return JsonResponse({
                'success': True,
                'already_enriched': True,
                'message': 'Ingredient already has Wikidata data',
                'data': {
                    'wikidata_entity': ingredient.wikidata_entity,
                    'description': getattr(ingredient, 'description', ''),
                    'calories_per_100g': getattr(ingredient, 'calories_per_100g', None),
                    'carbohydrates_g': getattr(ingredient, 'carbohydrates_g', None),
                    'protein_g': getattr(ingredient, 'protein_g', None),
                    'fat_g': getattr(ingredient, 'fat_g', None),
                    'fiber_g': getattr(ingredient, 'fiber_g', None),
                    'vitamin_c_mg': getattr(ingredient, 'vitamin_c_mg', None),
                    'calcium_mg': getattr(ingredient, 'calcium_mg', None),
                    'iron_mg': getattr(ingredient, 'iron_mg', None),
                }
            })
        
        # Import WikidataEnricher dynamically to avoid startup issues
        try:
            from rokumeals.mbg_app.external.wikidata_enricher import WikidataEnricher
            enricher = WikidataEnricher()
        except ImportError:
            logger.error("Failed to import WikidataEnricher")
            return JsonResponse({
                'success': False,
                'error': 'Wikidata enricher not available'
            })
        
        # Enrich the ingredient
        enrichment_result = enricher.enrich_ingredient(ingredient.name)
        
        if enrichment_result['wikidata_found']:
            # Update ingredient with enriched data
            nutritional_fields = {
                'calories_per_100g': 'calories_per_100g',
                'carbohydrates_g': 'carbohydrates_g',
                'protein_g': 'protein_g',
                'fat_g': 'fat_g',
                'fiber_g': 'fiber_g',
                'vitamin_c_mg': 'vitamin_c_mg',
                'calcium_mg': 'calcium_mg',
                'iron_mg': 'iron_mg',
                'sodium_mg': 'sodium_mg',
                'potassium_mg': 'potassium_mg'
            }
            
            updated_fields = []
            for source_field, target_field in nutritional_fields.items():
                if source_field in enrichment_result and enrichment_result[source_field]:
                    setattr(ingredient, target_field, enrichment_result[source_field])
                    updated_fields.append(target_field)
            
            # Update other fields
            if 'description' in enrichment_result:
                ingredient.description = enrichment_result['description'][:500]
                updated_fields.append('description')
            
            if 'wikidata_entity' in enrichment_result:
                ingredient.wikidata_entity = enrichment_result['wikidata_entity']
                updated_fields.append('wikidata_entity')
            
            # Save changes
            ingredient.save()
            
            logger.info(f"Successfully enriched ingredient '{ingredient.name}' with Wikidata data")
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully enriched {ingredient.name} with Wikidata data',
                'updated_fields': updated_fields,
                'data': {
                    'entity_label': enrichment_result.get('entity_label', ''),
                    'wikidata_entity': enrichment_result.get('wikidata_entity', ''),
                    'description': enrichment_result.get('description', ''),
                    'calories_per_100g': enrichment_result.get('calories_per_100g'),
                    'carbohydrates_g': enrichment_result.get('carbohydrates_g'),
                    'protein_g': enrichment_result.get('protein_g'),
                    'fat_g': enrichment_result.get('fat_g'),
                    'fiber_g': enrichment_result.get('fiber_g'),
                    'vitamin_c_mg': enrichment_result.get('vitamin_c_mg'),
                    'calcium_mg': enrichment_result.get('calcium_mg'),
                    'iron_mg': enrichment_result.get('iron_mg'),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': enrichment_result.get('error', 'No Wikidata entity found'),
                'message': f'Could not find Wikidata data for {ingredient.name}'
            })
            
    except Ingredient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ingredient not found'
        })
    except Exception as e:
        logger.error(f"Error enriching ingredient {ingredient_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
