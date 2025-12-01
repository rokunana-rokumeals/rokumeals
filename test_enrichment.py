#!/usr/bin/env python
"""
Test DBpedia enricher with Django models
"""
import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rokumeals.settings')
django.setup()

from rokumeals.mbg_app.models import Ingredient
from rokumeals.mbg_app.external.dbpedia_enricher_v2 import DBpediaEnricher

def test_enrichment():
    print("🔍 Testing DBpedia enrichment with Django models...")
    
    # Get some ingredients from database
    ingredients = Ingredient.nodes.all()[:5]
    print(f"Found {len(ingredients)} ingredients in database")
    
    # Initialize enricher
    enricher = DBpediaEnricher()
    
    for ingredient in ingredients:
        print(f"\n{'='*50}")
        print(f"Testing ingredient: {ingredient.name}")
        print('='*50)
        
        try:
            result = enricher.enrich_ingredient(ingredient.name)
            
            if result['dbpedia_found']:
                print(f"✅ Found DBpedia data!")
                print(f"Resource: {result.get('dbpedia_resource', 'N/A')}")
                
                # Print nutritional data if available
                nutritional_keys = ['calories_per_100g', 'carbohydrates_g', 'protein_g', 'fat_g']
                for key in nutritional_keys:
                    if key in result and result[key]:
                        print(f"{key}: {result[key]}")
                
                # Update ingredient with enriched data
                if 'calories_per_100g' in result:
                    ingredient.calories_per_100g = result['calories_per_100g']
                if 'description' in result:
                    ingredient.description = result['description'][:500]
                if 'dbpedia_resource' in result:
                    ingredient.dbpedia_resource = result['dbpedia_resource']
                
                # Save changes
                ingredient.save()
                print("💾 Updated ingredient in database")
                
            else:
                print(f"❌ No DBpedia data found")
                print(f"Error: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"💥 Error processing {ingredient.name}: {e}")
            
        print()

if __name__ == "__main__":
    test_enrichment()