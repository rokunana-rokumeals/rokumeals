#!/usr/bin/env python3
"""
Final Dataset Preparation for Meal Balance Grub Knowledge Graph
This script prepares the final processed datasets for Neo4j import
"""

import pandas as pd
import json
import re
import uuid

def clean_text(text):
    """Clean text for better Neo4j compatibility"""
    if pd.isna(text) or text == "":
        return ""
    text = str(text).strip()
    # Replace problematic characters
    text = text.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text

def generate_uuid():
    """Generate unique identifier for nodes"""
    return str(uuid.uuid4())

def prepare_final_datasets():
    """Create final datasets optimized for Knowledge Graph"""
    
    print("Loading existing CSV files...")
    
    # Load existing processed data
    recipes_df = pd.read_csv("recipes.csv")
    ingredients_df = pd.read_csv("ingredients.csv")
    ingredient_categories_df = pd.read_csv("ingredient_categories.csv")
    ingredient_calories_df = pd.read_csv("ingredient_calories.csv")
    recipe_ingredients_df = pd.read_csv("recipe_ingredients.csv")
    recipe_categories_df = pd.read_csv("recipe_categories.csv")
    
    print("Preparing final datasets for Neo4j...")
    
    # =============================================================================
    # 1. RECIPES NODE (Enhanced with unique IDs)
    # =============================================================================
    
    final_recipes = []
    for _, row in recipes_df.iterrows():
        recipe_id = generate_uuid()
        
        # Clean and process nutritional data
        calories = 0 if pd.isna(row['calories']) else float(row['calories'])
        protein = 0 if pd.isna(row['protein']) else float(row['protein'])
        fat = 0 if pd.isna(row['fat']) else float(row['fat'])
        sodium = 0 if pd.isna(row['sodium']) else float(row['sodium'])
        rating = 0 if pd.isna(row['rating']) else float(row['rating'])
        
        final_recipes.append({
            'recipe_id': recipe_id,
            'title': clean_text(row['title']),
            'rating': rating,
            'calories': calories,
            'protein': protein,
            'fat': fat,
            'sodium': sodium,
            'description': clean_text(row['desc']),
            'directions': clean_text(row['directions']),
            'ingredients_raw': clean_text(row['ingredients_raw'])
        })
    
    final_recipes_df = pd.DataFrame(final_recipes)
    
    # =============================================================================
    # 2. INGREDIENTS NODE (Enhanced)
    # =============================================================================
    
    # Create ingredient mapping with nutritional info (handle duplicates by taking first occurrence)
    ingredient_nutrition = ingredient_calories_df.drop_duplicates(subset=['Ingredient']).set_index('Ingredient').to_dict('index')
    ingredient_cats = ingredient_categories_df.drop_duplicates(subset=['Ingredient']).set_index('Ingredient').to_dict('index')
    
    final_ingredients = []
    for _, row in ingredients_df.iterrows():
        ingredient_id = generate_uuid()
        ingredient_name = clean_text(row['Ingredient'])
        
        # Get nutritional info if available
        nutrition = ingredient_nutrition.get(ingredient_name, {})
        category_info = ingredient_cats.get(ingredient_name, {})
        
        calories_per_100g = 0
        kj_per_100g = 0
        category = "Unknown"
        
        if nutrition:
            cal_text = nutrition.get('Cals_per100grams', '0 cal')
            kj_text = nutrition.get('KJ_per100grams', '0 kJ')
            
            # Extract numeric values
            cal_match = re.search(r'(\d+)', str(cal_text))
            kj_match = re.search(r'(\d+)', str(kj_text))
            
            calories_per_100g = int(cal_match.group(1)) if cal_match else 0
            kj_per_100g = int(kj_match.group(1)) if kj_match else 0
            
            category = nutrition.get('FoodCategory', 'Unknown')
        
        if category_info:
            category = category_info.get('Category', category)
        
        final_ingredients.append({
            'ingredient_id': ingredient_id,
            'name': ingredient_name,
            'category': category,
            'calories_per_100g': calories_per_100g,
            'kj_per_100g': kj_per_100g
        })
    
    final_ingredients_df = pd.DataFrame(final_ingredients)
    
    # =============================================================================
    # 3. CATEGORIES NODE
    # =============================================================================
    
    # Recipe categories
    recipe_cats = recipe_categories_df['category'].unique()
    ingredient_cats = final_ingredients_df['category'].unique()
    all_categories = list(set(list(recipe_cats) + list(ingredient_cats)))
    
    final_categories = []
    for cat in all_categories:
        if cat and cat != "Unknown":
            final_categories.append({
                'category_id': generate_uuid(),
                'name': clean_text(cat),
                'type': 'ingredient' if cat in ingredient_cats else 'recipe'
            })
    
    final_categories_df = pd.DataFrame(final_categories)
    
    # =============================================================================
    # 4. RELATIONSHIPS
    # =============================================================================
    
    # Recipe-Ingredient relationships
    recipe_title_to_id = final_recipes_df.set_index('title')['recipe_id'].to_dict()
    ingredient_name_to_id = final_ingredients_df.set_index('name')['ingredient_id'].to_dict()
    category_name_to_id = final_categories_df.set_index('name')['category_id'].to_dict()
    
    # Recipe-Ingredient CONTAINS relationships
    recipe_ingredient_rels = []
    for _, row in recipe_ingredients_df.iterrows():
        recipe_title = clean_text(row['title'])
        ingredient_name = clean_text(row['ingredient_clean'])
        
        recipe_id = recipe_title_to_id.get(recipe_title)
        ingredient_id = ingredient_name_to_id.get(ingredient_name)
        
        if recipe_id and ingredient_id:
            recipe_ingredient_rels.append({
                'recipe_id': recipe_id,
                'ingredient_id': ingredient_id
            })
    
    recipe_ingredient_rels_df = pd.DataFrame(recipe_ingredient_rels).drop_duplicates()
    
    # Recipe-Category BELONGS_TO relationships
    recipe_category_rels = []
    for _, row in recipe_categories_df.iterrows():
        recipe_title = clean_text(row['title'])
        category_name = clean_text(row['category'])
        
        recipe_id = recipe_title_to_id.get(recipe_title)
        category_id = category_name_to_id.get(category_name)
        
        if recipe_id and category_id:
            recipe_category_rels.append({
                'recipe_id': recipe_id,
                'category_id': category_id
            })
    
    recipe_category_rels_df = pd.DataFrame(recipe_category_rels).drop_duplicates()
    
    # Ingredient-Category BELONGS_TO relationships
    ingredient_category_rels = []
    for _, row in final_ingredients_df.iterrows():
        if row['category'] != 'Unknown':
            category_id = category_name_to_id.get(row['category'])
            if category_id:
                ingredient_category_rels.append({
                    'ingredient_id': row['ingredient_id'],
                    'category_id': category_id
                })
    
    ingredient_category_rels_df = pd.DataFrame(ingredient_category_rels).drop_duplicates()
    
    # =============================================================================
    # SAVE FINAL DATASETS
    # =============================================================================
    
    # Save node files
    final_recipes_df.to_csv("final_recipes.csv", index=False)
    final_ingredients_df.to_csv("final_ingredients.csv", index=False)
    final_categories_df.to_csv("final_categories.csv", index=False)
    
    # Save relationship files
    recipe_ingredient_rels_df.to_csv("final_recipe_ingredient_rels.csv", index=False)
    recipe_category_rels_df.to_csv("final_recipe_category_rels.csv", index=False)
    ingredient_category_rels_df.to_csv("final_ingredient_category_rels.csv", index=False)
    
    # =============================================================================
    # GENERATE SUMMARY STATISTICS
    # =============================================================================
    
    stats = {
        "total_recipes": len(final_recipes_df),
        "total_ingredients": len(final_ingredients_df),
        "total_categories": len(final_categories_df),
        "recipe_ingredient_relationships": len(recipe_ingredient_rels_df),
        "recipe_category_relationships": len(recipe_category_rels_df),
        "ingredient_category_relationships": len(ingredient_category_rels_df),
        "avg_rating": final_recipes_df['rating'].mean(),
        "avg_calories": final_recipes_df['calories'].mean(),
        "top_categories": final_categories_df['name'].value_counts().head(10).to_dict()
    }
    
    with open("dataset_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    
    print("\n=== FINAL DATASET STATISTICS ===")
    print(f"Recipes: {stats['total_recipes']:,}")
    print(f"Ingredients: {stats['total_ingredients']:,}")
    print(f"Categories: {stats['total_categories']:,}")
    print(f"Recipe-Ingredient relationships: {stats['recipe_ingredient_relationships']:,}")
    print(f"Recipe-Category relationships: {stats['recipe_category_relationships']:,}")
    print(f"Ingredient-Category relationships: {stats['ingredient_category_relationships']:,}")
    print(f"Average Recipe Rating: {stats['avg_rating']:.2f}")
    print(f"Average Recipe Calories: {stats['avg_calories']:.0f}")
    
    print("\n✅ Final datasets generated successfully!")
    print("Files created:")
    print("- final_recipes.csv")
    print("- final_ingredients.csv") 
    print("- final_categories.csv")
    print("- final_recipe_ingredient_rels.csv")
    print("- final_recipe_category_rels.csv")
    print("- final_ingredient_category_rels.csv")
    print("- dataset_stats.json")

if __name__ == "__main__":
    prepare_final_datasets()