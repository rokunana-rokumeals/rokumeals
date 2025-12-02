import json
import csv
from django.core.management.base import BaseCommand
from neomodel import db
import os

class Command(BaseCommand):
    help = 'Export data for external embedding generation'

    def add_arguments(self, parser):
        parser.add_argument('--format', choices=['json', 'csv'], default='json')
        parser.add_argument('--output-dir', default='embedding_data')
        parser.add_argument('--limit', type=int, help='Limit number of items')
        parser.add_argument('--all', action='store_true', help='Export all data without limit')
        parser.add_argument('--type', choices=['recipe', 'ingredient', 'category'], help='Export specific type only')

    def handle(self, *args, **options):
        os.makedirs(options['output_dir'], exist_ok=True)
        
        # Handle --all flag
        limit = options['limit']
        if options['all']:
            limit = None
            self.stdout.write(self.style.WARNING('Exporting ALL data (no limit)'))
        
        # Check if specific type is requested
        export_type = options.get('type')
        
        recipe_data = []
        ingredient_data = []
        category_data = []
        
        # Export based on type selection
        if not export_type or export_type == 'recipe':
            recipe_data = self._export_recipes(limit)
        
        if not export_type or export_type == 'ingredient':
            ingredient_data = self._export_ingredients(limit)
        
        if not export_type or export_type == 'category':
            category_data = self._export_categories()
        
        # Save data
        if options['format'] == 'json':
            self._save_json(options['output_dir'], recipe_data, ingredient_data, category_data)
        else:
            self._save_csv(options['output_dir'], recipe_data, ingredient_data, category_data)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully exported:\n'
                f'- {len(recipe_data)} recipes\n'
                f'- {len(ingredient_data)} ingredients\n'
                f'- {len(category_data)} categories\n'
                f'to {options["output_dir"]}/'
            )
        )

    def _export_recipes(self, limit):
        """Export recipe data using Neo4j queries"""
        query = """
        MATCH (r:Recipe)
        OPTIONAL MATCH (r)-[:HAS_INGREDIENT]->(i:Ingredient)
        OPTIONAL MATCH (r)-[:BELONGS_TO_CATEGORY]->(c:Category)
        WITH r, 
             collect(DISTINCT i.name) as ingredients,
             collect(DISTINCT c.name) as categories
        RETURN r.id as id, r.title as title, r.description as description,
               ingredients, categories
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results, _ = db.cypher_query(query)
            recipe_data = []
            
            for result in results:
                recipe_id, title, description, ingredients, categories = result
                
                ingredients_text = ', '.join(ingredients) if ingredients else ''
                categories_text = ', '.join(categories) if categories else ''
                
                text_for_embedding = f"{title or 'Recipe'}. {description or ''}. Ingredients: {ingredients_text}. Categories: {categories_text}."
                
                recipe_data.append({
                    'id': str(recipe_id),
                    'type': 'recipe',
                    'text': self._clean_text(text_for_embedding),
                    'title': title or 'Recipe',
                    'description': description or '',
                    'ingredients': ingredients_text,
                    'categories': categories_text
                })
            
            return recipe_data
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error exporting recipes: {e}'))
            return []

    def _export_ingredients(self, limit):
        """Export ingredient data using Neo4j queries"""
        query = """
        MATCH (i:Ingredient)
        OPTIONAL MATCH (r:Recipe)-[:HAS_INGREDIENT]->(i)
        WITH i,
             collect(DISTINCT r.title)[..5] as recipe_names
        RETURN i.id as id, i.name as name,
               i.calories_per_100g as calories,
               i.protein_g as protein,
               i.carbohydrates_g as carbs,
               recipe_names
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            results, _ = db.cypher_query(query)
            ingredient_data = []
            
            for result in results:
                ing_id, name, calories, protein, carbs, recipe_names = result
                
                nutrition_info = []
                if calories:
                    nutrition_info.append(f"calories: {calories}")
                if protein:
                    nutrition_info.append(f"protein: {protein}g")
                if carbs:
                    nutrition_info.append(f"carbs: {carbs}g")
                
                nutrition_text = ', '.join(nutrition_info)
                recipe_names_text = ', '.join(recipe_names) if recipe_names else ''
                
                text_for_embedding = f"{name or 'Ingredient'}. Nutrition: {nutrition_text}. Used in recipes: {recipe_names_text}."
                
                ingredient_data.append({
                    'id': str(ing_id),
                    'type': 'ingredient',
                    'text': self._clean_text(text_for_embedding),
                    'name': name or 'Ingredient',
                    'nutrition': nutrition_text,
                    'common_recipes': recipe_names_text
                })
            
            return ingredient_data
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error exporting ingredients: {e}'))
            return []

    def _export_categories(self):
        """Export category data using Neo4j queries"""
        query = """
        MATCH (c:Category)
        OPTIONAL MATCH (item)-[:BELONGS_TO_CATEGORY]->(c)
        WITH c, 
             collect(DISTINCT item.title)[..10] as recipe_items,
             collect(DISTINCT item.name)[..10] as ingredient_items
        RETURN c.id as id, c.name as name, c.type as type,
               recipe_items, ingredient_items
        """
        
        try:
            results, _ = db.cypher_query(query)
            category_data = []
            
            for result in results:
                cat_id, name, cat_type, recipe_items, ingredient_items = result
                
                # Combine items based on category type
                if cat_type == 'recipe':
                    items = recipe_items or []
                else:
                    items = ingredient_items or []
                
                items_text = ', '.join(items) if items else ''
                text_for_embedding = f"{name or 'Category'}. Type: {cat_type or 'general'}. Contains: {items_text}."
                
                category_data.append({
                    'id': str(cat_id),
                    'type': 'category',
                    'text': self._clean_text(text_for_embedding),
                    'name': name or 'Category',
                    'category_type': cat_type or 'general',
                    'sample_items': items_text
                })
            
            return category_data
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error exporting categories: {e}'))
            return []

    def _clean_text(self, text):
        """Clean text for embedding generation"""
        return text.replace('\n', ' ').replace('\r', ' ').strip()

    def _save_json(self, output_dir, recipes, ingredients, categories):
        with open(f'{output_dir}/recipes.json', 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        
        with open(f'{output_dir}/ingredients.json', 'w', encoding='utf-8') as f:
            json.dump(ingredients, f, ensure_ascii=False, indent=2)
        
        with open(f'{output_dir}/categories.json', 'w', encoding='utf-8') as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)

    def _save_csv(self, output_dir, recipes, ingredients, categories):
        # Save recipes CSV
        with open(f'{output_dir}/recipes.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'type', 'text', 'title', 'description', 'ingredients', 'categories'])
            writer.writeheader()
            writer.writerows(recipes)
        
        # Save ingredients CSV
        with open(f'{output_dir}/ingredients.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'type', 'text', 'name', 'nutrition', 'common_recipes'])
            writer.writeheader()
            writer.writerows(ingredients)
        
        # Save categories CSV
        with open(f'{output_dir}/categories.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'type', 'text', 'name', 'category_type', 'sample_items'])
            writer.writeheader()
            writer.writerows(categories)