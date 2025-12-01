# Meal Balance Grub - Dataset Explorer

This notebook explores the processed dataset for the Knowledge Graph project.

## Dataset Statistics

```python
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Load statistics
with open('dataset_stats.json', 'r') as f:
    stats = json.load(f)

print("=== MEAL BALANCE GRUB KNOWLEDGE GRAPH DATASET ===")
print(f"📊 Total Recipes: {stats['total_recipes']:,}")
print(f"🥗 Total Ingredients: {stats['total_ingredients']:,}")
print(f"📁 Total Categories: {stats['total_categories']:,}")
print(f"🔗 Recipe-Ingredient Relationships: {stats['recipe_ingredient_relationships']:,}")
print(f"⭐ Average Recipe Rating: {stats['avg_rating']:.2f}")
print(f"🔥 Average Recipe Calories: {stats['avg_calories']:.0f}")
```

## Data Preview

### Recipes
```python
recipes_df = pd.read_csv('final_recipes.csv')
print("Sample Recipes:")
print(recipes_df[['title', 'rating', 'calories', 'protein']].head())

print(f"\nRecipes with ratings: {len(recipes_df[recipes_df['rating'] > 0])}")
print(f"Recipes with nutritional info: {len(recipes_df[recipes_df['calories'] > 0])}")
```

### Ingredients  
```python
ingredients_df = pd.read_csv('final_ingredients.csv')
print("Sample Ingredients:")
print(ingredients_df[['name', 'category', 'calories_per_100g']].head())

print(f"\nIngredients with calorie info: {len(ingredients_df[ingredients_df['calories_per_100g'] > 0])}")
print(f"Unique ingredient categories: {ingredients_df['category'].nunique()}")
```

### Categories
```python
categories_df = pd.read_csv('final_categories.csv')
print("Sample Categories:")
print(categories_df.head())

print(f"\nRecipe categories: {len(categories_df[categories_df['type'] == 'recipe'])}")
print(f"Ingredient categories: {len(categories_df[categories_df['type'] == 'ingredient'])}")
```

## Data Visualizations

### Recipe Ratings Distribution
```python
plt.figure(figsize=(10, 6))
rated_recipes = recipes_df[recipes_df['rating'] > 0]
plt.hist(rated_recipes['rating'], bins=20, alpha=0.7, edgecolor='black')
plt.title('Distribution of Recipe Ratings')
plt.xlabel('Rating')
plt.ylabel('Number of Recipes')
plt.grid(True, alpha=0.3)
plt.show()
```

### Calorie Distribution
```python
plt.figure(figsize=(10, 6))
calorie_recipes = recipes_df[(recipes_df['calories'] > 0) & (recipes_df['calories'] < 2000)]  # Filter outliers
plt.hist(calorie_recipes['calories'], bins=50, alpha=0.7, edgecolor='black')
plt.title('Distribution of Recipe Calories (0-2000 cal)')
plt.xlabel('Calories')
plt.ylabel('Number of Recipes')
plt.grid(True, alpha=0.3)
plt.show()
```

### Top 10 Recipe Categories
```python
recipe_cat_rels = pd.read_csv('final_recipe_category_rels.csv')
recipe_cats = recipe_cat_rels.merge(categories_df, on='category_id', how='left')
cat_counts = recipe_cats['name'].value_counts().head(10)

plt.figure(figsize=(12, 6))
cat_counts.plot(kind='bar')
plt.title('Top 10 Recipe Categories')
plt.xlabel('Category')
plt.ylabel('Number of Recipes')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
```

### Ingredient Calorie Distribution
```python
plt.figure(figsize=(10, 6))
calorie_ingredients = ingredients_df[ingredients_df['calories_per_100g'] > 0]
plt.hist(calorie_ingredients['calories_per_100g'], bins=50, alpha=0.7, edgecolor='black')
plt.title('Distribution of Ingredient Calories per 100g')
plt.xlabel('Calories per 100g')
plt.ylabel('Number of Ingredients')
plt.grid(True, alpha=0.3)
plt.show()
```

### Top 10 High-Calorie Ingredients
```python
high_cal = ingredients_df.nlargest(10, 'calories_per_100g')
plt.figure(figsize=(12, 6))
plt.bar(range(len(high_cal)), high_cal['calories_per_100g'])
plt.title('Top 10 High-Calorie Ingredients')
plt.xlabel('Ingredient')
plt.ylabel('Calories per 100g')
plt.xticks(range(len(high_cal)), high_cal['name'], rotation=45, ha='right')
plt.tight_layout()
plt.show()
```

## Relationship Analysis

### Recipe-Ingredient Network Stats
```python
recipe_ing_rels = pd.read_csv('final_recipe_ingredient_rels.csv')

# Ingredients per recipe
ingredients_per_recipe = recipe_ing_rels.groupby('recipe_id').size()
print(f"Average ingredients per recipe: {ingredients_per_recipe.mean():.2f}")
print(f"Max ingredients in a recipe: {ingredients_per_recipe.max()}")
print(f"Min ingredients in a recipe: {ingredients_per_recipe.min()}")

# Recipes per ingredient  
recipes_per_ingredient = recipe_ing_rels.groupby('ingredient_id').size()
print(f"\nAverage recipes per ingredient: {recipes_per_ingredient.mean():.2f}")
print(f"Most used ingredient appears in {recipes_per_ingredient.max()} recipes")
```

### Most Popular Ingredients
```python
popular_ingredients = recipe_ing_rels.merge(ingredients_df, on='ingredient_id', how='left')
top_ingredients = popular_ingredients['name'].value_counts().head(15)

plt.figure(figsize=(12, 6))
top_ingredients.plot(kind='bar')
plt.title('Top 15 Most Popular Ingredients')
plt.xlabel('Ingredient')
plt.ylabel('Number of Recipes')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.show()
```

## Data Quality Assessment

```python
print("=== DATA QUALITY REPORT ===")

# Recipes
recipes_with_rating = len(recipes_df[recipes_df['rating'] > 0])
recipes_with_calories = len(recipes_df[recipes_df['calories'] > 0])
recipes_with_description = len(recipes_df[recipes_df['description'].str.len() > 0])

print(f"\nRecipes Data Quality:")
print(f"- With ratings: {recipes_with_rating:,} ({recipes_with_rating/len(recipes_df)*100:.1f}%)")
print(f"- With calorie info: {recipes_with_calories:,} ({recipes_with_calories/len(recipes_df)*100:.1f}%)")
print(f"- With descriptions: {recipes_with_description:,} ({recipes_with_description/len(recipes_df)*100:.1f}%)")

# Ingredients  
ingredients_with_calories = len(ingredients_df[ingredients_df['calories_per_100g'] > 0])
ingredients_with_category = len(ingredients_df[ingredients_df['category'] != 'Unknown'])

print(f"\nIngredients Data Quality:")
print(f"- With calorie info: {ingredients_with_calories:,} ({ingredients_with_calories/len(ingredients_df)*100:.1f}%)")
print(f"- With categories: {ingredients_with_category:,} ({ingredients_with_category/len(ingredients_df)*100:.1f}%)")
```

## Ready for Knowledge Graph!

The dataset is now prepared and ready for import into Neo4j. Key features:

✅ **Comprehensive Data**: 20K+ recipes, 4.6K+ ingredients, 700+ categories  
✅ **Rich Relationships**: Recipe-ingredient, recipe-category, ingredient-category connections  
✅ **Unique IDs**: All entities have unique identifiers for proper graph structure  
✅ **Nutritional Data**: Calorie and macro information for enhanced queries  
✅ **Clean Structure**: Processed and normalized data ready for property graph import  

### Next Steps:
1. **Neo4j Setup**: Install Neo4j and create a new database
2. **CSV Import**: Place the final CSV files in Neo4j's import directory  
3. **Run Cypher**: Execute the `import_final.cypher` script
4. **Build Application**: Create the web interface with search, query console, and info box features
5. **External Data**: Integrate with DBpedia/Wikidata for ingredient enrichment