"""
Create indexes untuk improve performance search di Neo4j
"""
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rokumeals.settings')
django.setup()

from neomodel import db

def create_indexes():
    """Create indexes untuk improve search performance"""
    print("Creating Neo4j indexes for better performance...")
    
    indexes = [
        # Recipe indexes
        "CREATE INDEX recipe_title_index IF NOT EXISTS FOR (r:Recipe) ON (r.title)",
        "CREATE INDEX recipe_id_index IF NOT EXISTS FOR (r:Recipe) ON (r.recipe_id)",
        "CREATE INDEX recipe_rating_index IF NOT EXISTS FOR (r:Recipe) ON (r.rating)",
        "CREATE INDEX recipe_calories_index IF NOT EXISTS FOR (r:Recipe) ON (r.calories)",
        
        # Ingredient indexes
        "CREATE INDEX ingredient_name_index IF NOT EXISTS FOR (i:Ingredient) ON (i.name)",
        "CREATE INDEX ingredient_id_index IF NOT EXISTS FOR (i:Ingredient) ON (i.ingredient_id)",
        "CREATE INDEX ingredient_category_index IF NOT EXISTS FOR (i:Ingredient) ON (i.category)",
        "CREATE INDEX ingredient_calories_index IF NOT EXISTS FOR (i:Ingredient) ON (i.calories_per_100g)",
        
        # Category indexes
        "CREATE INDEX category_name_index IF NOT EXISTS FOR (c:Category) ON (c.name)",
        "CREATE INDEX category_id_index IF NOT EXISTS FOR (c:Category) ON (c.category_id)",
        "CREATE INDEX category_type_index IF NOT EXISTS FOR (c:Category) ON (c.type)",
        
        # Text search indexes for better search performance
        "CREATE TEXT INDEX recipe_title_text_index IF NOT EXISTS FOR (r:Recipe) ON (r.title)",
        "CREATE TEXT INDEX ingredient_name_text_index IF NOT EXISTS FOR (i:Ingredient) ON (i.name)",
        "CREATE TEXT INDEX category_name_text_index IF NOT EXISTS FOR (c:Category) ON (c.name)",
    ]
    
    for index_query in indexes:
        try:
            db.cypher_query(index_query)
            print(f"✅ {index_query}")
        except Exception as e:
            print(f"❌ {index_query}")
            print(f"   Error: {e}")

def check_indexes():
    """Check existing indexes"""
    print("\nChecking existing indexes...")
    try:
        result, meta = db.cypher_query("SHOW INDEXES")
        print(f"Found {len(result)} indexes:")
        for row in result:
            print(f"  - {row[1]} ({row[2]}) on {row[8]}")
    except Exception as e:
        print(f"Error checking indexes: {e}")

if __name__ == "__main__":
    create_indexes()
    check_indexes()