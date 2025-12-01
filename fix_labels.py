#!/usr/bin/env python
"""
Script untuk update labels di Neo4j dari lowercase ke uppercase
untuk match dengan Django models
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from neomodel import config, db
    
    # Setup connection
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME') 
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    db_url = f"{NEO4J_URI.replace('neo4j+s://', 'bolt+s://')}"
    db_url = db_url.replace('://', f"://{NEO4J_USERNAME}:{NEO4J_PASSWORD}@")
    
    config.DATABASE_URL = db_url
    config.DATABASE_NAME = NEO4J_DATABASE
    
    print("Updating labels to match Django models...")
    
    # Update recipe label
    print("Updating recipe -> Recipe labels...")
    recipe_update = """
    MATCH (n:recipe)
    SET n:Recipe
    REMOVE n:recipe
    RETURN count(n) as updated
    """
    result = db.cypher_query(recipe_update)
    print(f"Updated {result[0][0][0]} recipe nodes")
    
    # Update ingredient label  
    print("Updating ingredient -> Ingredient labels...")
    ingredient_update = """
    MATCH (n:ingredient)
    SET n:Ingredient
    REMOVE n:ingredient
    RETURN count(n) as updated
    """
    result = db.cypher_query(ingredient_update)
    print(f"Updated {result[0][0][0]} ingredient nodes")
    
    # Update category label
    print("Updating category -> Category labels...")
    category_update = """
    MATCH (n:category)
    SET n:Category
    REMOVE n:category
    RETURN count(n) as updated
    """
    result = db.cypher_query(category_update)
    print(f"Updated {result[0][0][0]} category nodes")
    
    # Verify updates
    print("\n=== VERIFICATION ===")
    labels_query = """
    MATCH (n)
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    """
    results = db.cypher_query(labels_query)
    
    if results[0]:
        for row in results[0]:
            print(f"{row[0]}: {row[1]} nodes")
    
    print("\nLabel update completed!")

except Exception as e:
    print(f"Error: {e}")