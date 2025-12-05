import os
import sys
import django

# Setup Django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rokumeals.settings')
django.setup()

from neomodel import db

def check_absinthe_issue():
    print("🔍 Checking Absinthe ingredient and recipe relationships...")
    
    # 1. Check all Absinthe ingredients
    query1 = """
    MATCH (i:Ingredient)
    WHERE toLower(i.name) = 'absinthe'
    OPTIONAL MATCH (i)<-[:CONTAINS]-(r:Recipe)
    RETURN i.name as name, i.ingredient_id as id, i.category as category, 
           count(r) as recipe_count, collect(r.title) as recipe_titles
    ORDER BY i.name
    """
    
    results1, _ = db.cypher_query(query1)
    print("\n📋 Absinthe ingredients and their recipe usage:")
    
    for row in results1:
        name, ing_id, category, rec_count, recipe_titles = row
        print(f'Name: "{name}"')
        print(f'  ID: {ing_id[:8]}...')
        print(f'  Category: {category}')
        print(f'  Recipe count: {rec_count}')
        if recipe_titles:
            print(f'  Recipes: {recipe_titles}')
        print()
    
    # 2. Check if there are still duplicates after normalization
    query2 = """
    MATCH (i:Ingredient)
    WHERE toLower(i.name) = 'absinthe'
    RETURN count(i) as ingredient_count
    """
    
    results2, _ = db.cypher_query(query2)
    duplicate_count = results2[0][0]
    print(f"🔢 Total Absinthe ingredients found: {duplicate_count}")
    
    if duplicate_count > 1:
        print("⚠️  Still have duplicates! Normalization didn't work completely.")
        
        # Find what went wrong
        query3 = """
        MATCH (i:Ingredient)
        WHERE toLower(i.name) = 'absinthe'
        RETURN i.ingredient_id, i.name, i.category
        """
        results3, _ = db.cypher_query(query3)
        
        print("\nAll Absinthe variants still in DB:")
        for row in results3:
            ing_id, name, category = row
            print(f"  - {name} (ID: {ing_id[:8]}..., Category: {category})")
    
    # 3. Check specifically which ingredient the detail view is trying to show
    print("\n🔍 Debug: Let's see which Absinthe ingredient is being accessed...")
    
    # Check the old lowercase absinthe ID (if it still exists)
    old_id = "38c38a29-bf3d-4b05-a1b5-bb909231e7d0"
    query4 = """
    MATCH (i:Ingredient {ingredient_id: $old_id})
    OPTIONAL MATCH (i)<-[:CONTAINS]-(r:Recipe)
    RETURN i.name, i.category, count(r) as recipe_count, collect(r.title)[0..3] as sample_recipes
    """
    
    results4, _ = db.cypher_query(query4, {"old_id": old_id})
    if results4:
        name, category, rec_count, sample_recipes = results4[0]
        print(f"Old lowercase absinthe ID still exists:")
        print(f"  Name: {name}, Category: {category}, Recipes: {rec_count}")
        print(f"  Sample recipes: {sample_recipes}")
    else:
        print("Old lowercase absinthe ID not found (good!)")
    
    # Check the proper Absinthe ID
    proper_id = "39a956ee-137e-4b68-8b3f-d0b0c4751dce"
    query5 = """
    MATCH (i:Ingredient {ingredient_id: $proper_id})
    OPTIONAL MATCH (i)<-[:CONTAINS]-(r:Recipe)
    RETURN i.name, i.category, count(r) as recipe_count, collect(r.title)[0..3] as sample_recipes
    """
    
    results5, _ = db.cypher_query(query5, {"proper_id": proper_id})
    if results5:
        name, category, rec_count, sample_recipes = results5[0]
        print(f"\nProper Absinthe ID:")
        print(f"  Name: {name}, Category: {category}, Recipes: {rec_count}")
        print(f"  Sample recipes: {sample_recipes}")
    else:
        print("Proper Absinthe ID not found!")

if __name__ == "__main__":
    check_absinthe_issue()