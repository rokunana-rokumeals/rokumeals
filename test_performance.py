"""
Test performance issues di MBG Knowledge Graph
"""
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rokumeals.settings')
django.setup()

import time
from neomodel import db
from mbg_app.models import Recipe, Ingredient, Category

def test_count_performance():
    """Test performa counting methods"""
    print("Testing count performance...")
    
    # Test 1: nodes.all() method (SLOW)
    print("\n1. Testing Recipe.nodes.all() method:")
    start = time.time()
    try:
        count = len(Recipe.nodes.all())
        end = time.time()
        print(f"   Result: {count} recipes in {end-start:.2f} seconds")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Direct Cypher COUNT (FAST)
    print("\n2. Testing direct Cypher COUNT:")
    start = time.time()
    result, meta = db.cypher_query("MATCH (r:Recipe) RETURN count(r) as count")
    count = result[0][0]
    end = time.time()
    print(f"   Result: {count} recipes in {end-start:.2f} seconds")
    
    # Test 3: Ingredient count comparison
    print("\n3. Testing Ingredient counts:")
    start = time.time()
    result, meta = db.cypher_query("MATCH (i:Ingredient) RETURN count(i) as count")
    ingredient_count = result[0][0]
    end = time.time()
    print(f"   Cypher: {ingredient_count} ingredients in {end-start:.2f} seconds")
    
    # Test 4: Category count
    print("\n4. Testing Category counts:")
    start = time.time()
    result, meta = db.cypher_query("MATCH (c:Category) RETURN count(c) as count")
    category_count = result[0][0]
    end = time.time()
    print(f"   Cypher: {category_count} categories in {end-start:.2f} seconds")

def test_search_performance():
    """Test search performance"""
    print("\n\nTesting search performance...")
    
    search_term = "chicken"
    
    # Test recipe search
    print(f"\n1. Searching recipes for '{search_term}':")
    start = time.time()
    try:
        recipes = Recipe.search_by_name(search_term, 10)
        end = time.time()
        print(f"   Found {len(list(recipes))} recipes in {end-start:.2f} seconds")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_count_performance()
    test_search_performance()