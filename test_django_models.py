#!/usr/bin/env python
"""
Test Django models dengan data yang sudah ada
"""
import os
import django
from dotenv import load_dotenv

load_dotenv()

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rokumeals.settings')
django.setup()

try:
    from mbg_app.models import Recipe, Ingredient, Category
    
    print("=== TESTING DJANGO MODELS ===")
    
    # Test counts
    recipe_count = Recipe.nodes.count() if hasattr(Recipe.nodes, 'count') else len(Recipe.nodes.all())
    print(f"Recipes: {recipe_count}")
    
    ingredient_count = Ingredient.nodes.count() if hasattr(Ingredient.nodes, 'count') else len(Ingredient.nodes.all())
    print(f"Ingredients: {ingredient_count}")
    
    category_count = Category.nodes.count() if hasattr(Category.nodes, 'count') else len(Category.nodes.all())
    print(f"Categories: {category_count}")
    
    # Test sample data
    print("\n=== SAMPLE RECIPES ===")
    try:
        recipes = Recipe.nodes.all()[:5]
        for recipe in recipes:
            print(f"- {recipe.title} (Rating: {recipe.rating})")
    except Exception as e:
        print(f"Error getting recipes: {e}")
    
    print("\n=== SAMPLE INGREDIENTS ===")
    try:
        ingredients = Ingredient.nodes.all()[:5]
        for ingredient in ingredients:
            print(f"- {ingredient.name} ({ingredient.category})")
    except Exception as e:
        print(f"Error getting ingredients: {e}")
        
    print("\n=== SAMPLE CATEGORIES ===")
    try:
        categories = Category.nodes.all()[:5]
        for category in categories:
            print(f"- {category.name} ({category.type})")
    except Exception as e:
        print(f"Error getting categories: {e}")
        
    # Test search functionality
    print("\n=== TESTING SEARCH ===")
    try:
        # Search for chicken recipes
        chicken_recipes = Recipe.nodes.filter(title__icontains="chicken")[:3]
        print("Chicken recipes:")
        for recipe in chicken_recipes:
            print(f"  - {recipe.title}")
    except Exception as e:
        print(f"Error searching recipes: {e}")
        
    try:
        # Search for garlic ingredient
        garlic_ingredients = Ingredient.nodes.filter(name__icontains="garlic")[:3]
        print("Garlic ingredients:")
        for ingredient in garlic_ingredients:
            print(f"  - {ingredient.name}")
    except Exception as e:
        print(f"Error searching ingredients: {e}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()