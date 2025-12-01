#!/usr/bin/env python
"""
Script sederhana untuk test koneksi Neo4j dan cek data
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from neomodel import config, db
    
    # Setup connection
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME') 
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    # Create connection string
    db_url = f"{NEO4J_URI.replace('neo4j+s://', 'bolt+s://')}"
    db_url = db_url.replace('://', f"://{NEO4J_USERNAME}:{NEO4J_PASSWORD}@")
    
    print(f"Connecting to: {db_url.replace(NEO4J_PASSWORD, '***')}")
    
    config.DATABASE_URL = db_url
    config.DATABASE_NAME = NEO4J_DATABASE
    
    # Test connection
    print("Testing connection...")
    result = db.cypher_query("RETURN 'Hello Neo4j!' as message")
    print(f"Connection successful: {result[0][0][0]}")
    
    # Check data counts
    print("\n=== DATA COUNTS ===")
    
    # Count nodes by label
    labels_query = """
    MATCH (n)
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    """
    results = db.cypher_query(labels_query)
    
    if results[0]:
        for row in results[0]:
            print(f"{row[0]}: {row[1]} nodes")
    else:
        print("No nodes found in database")
    
    # Count relationships
    rels_query = """
    MATCH ()-[r]->()
    RETURN type(r) as rel_type, count(r) as count
    ORDER BY count DESC
    """
    rel_results = db.cypher_query(rels_query)
    
    print("\n=== RELATIONSHIP COUNTS ===")
    if rel_results[0]:
        for row in rel_results[0]:
            print(f"{row[0]}: {row[1]} relationships")
    else:
        print("No relationships found in database")
    
    # Sample queries
    print("\n=== SAMPLE DATA ===")
    
    # Sample recipes
    recipe_query = """
    MATCH (r)
    WHERE 'Recipe' IN labels(r)
    RETURN r.title, r.rating
    LIMIT 5
    """
    recipe_results = db.cypher_query(recipe_query)
    
    if recipe_results[0]:
        print("Sample recipes:")
        for row in recipe_results[0]:
            print(f"  - {row[0]} (Rating: {row[1]})")
    else:
        print("No Recipe nodes found")
    
    # Sample ingredients
    ingredient_query = """
    MATCH (i)
    WHERE 'Ingredient' IN labels(i)
    RETURN i.name, i.category
    LIMIT 5
    """
    ingredient_results = db.cypher_query(ingredient_query)
    
    if ingredient_results[0]:
        print("Sample ingredients:")
        for row in ingredient_results[0]:
            print(f"  - {row[0]} ({row[1]})")
    else:
        print("No Ingredient nodes found")

except ImportError as e:
    print(f"Import error: {e}")
    print("Please install neomodel: pip install neomodel")
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")