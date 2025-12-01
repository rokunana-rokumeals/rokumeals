"""
Django Management Command untuk import data MBG ke Neo4j
Usage: python manage.py import_mbg_data
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd
import os
from tqdm import tqdm

from mbg_app.models import Recipe, Ingredient, Category


class Command(BaseCommand):
    help = 'Import MBG dataset from CSV files to Neo4j'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='datasets',
            help='Directory containing CSV files (default: datasets)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for processing (default: 100)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before import',
        )

    def handle(self, *args, **options):
        self.data_dir = options['data_dir']
        self.batch_size = options['batch_size']
        
        self.stdout.write(
            self.style.SUCCESS('Starting MBG data import to Neo4j...')
        )
        
        if options['clear']:
            self.clear_existing_data()
        
        try:
            # Import in order: Categories -> Ingredients -> Recipes -> Relationships
            self.import_categories()
            self.import_ingredients() 
            self.import_recipes()
            self.import_relationships()
            
            self.stdout.write(
                self.style.SUCCESS('Data import completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Import failed: {str(e)}')
            )
            raise

    def clear_existing_data(self):
        """Clear existing Neo4j data"""
        self.stdout.write('Clearing existing data...')
        
        # Clear relationships first using Cypher
        from neomodel import db
        
        try:
            # Delete all relationships
            db.cypher_query("MATCH ()-[r]->() DELETE r")
            self.stdout.write('Cleared relationships...')
            
            # Delete all nodes
            db.cypher_query("MATCH (n) DELETE n")
            self.stdout.write('Cleared nodes...')
            
        except Exception as e:
            self.stdout.write(f'Error clearing data: {str(e)}')
            # Try alternative method
            try:
                # Clear nodes one by one
                recipes = Recipe.nodes.all()
                for recipe in recipes:
                    recipe.delete()
                
                ingredients = Ingredient.nodes.all()
                for ingredient in ingredients:
                    ingredient.delete()
                    
                categories = Category.nodes.all()
                for category in categories:
                    category.delete()
                    
            except Exception as e2:
                self.stdout.write(f'Alternative clear failed: {str(e2)}')
        
        self.stdout.write(
            self.style.WARNING('Existing data cleared')
        )

    def get_csv_path(self, filename):
        """Get full path to CSV file"""
        return os.path.join(self.data_dir, filename)

    def import_categories(self):
        """Import categories from CSV"""
        self.stdout.write('Importing categories...')
        
        csv_path = self.get_csv_path('final_categories.csv')
        df = pd.read_csv(csv_path)
        
        categories = []
        created = 0
        skipped = 0
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Categories"):
            # Check if category already exists
            try:
                existing = Category.nodes.get(category_id=row['category_id'])
                skipped += 1
                continue
            except Category.DoesNotExist:
                pass
            
            category = Category(
                category_id=row['category_id'],
                name=row['name'],
                type=row['type']
            )
            categories.append(category)
            
            if len(categories) >= self.batch_size:
                self.save_batch(categories)
                created += len(categories)
                categories = []
        
        if categories:
            self.save_batch(categories)
            created += len(categories)
        
        self.stdout.write(
            self.style.SUCCESS(f'Imported {created} categories, skipped {skipped} duplicates')
        )

    def import_ingredients(self):
        """Import ingredients from CSV"""
        self.stdout.write('Importing ingredients...')
        
        csv_path = self.get_csv_path('final_ingredients.csv')
        df = pd.read_csv(csv_path)
        
        ingredients = []
        created = 0
        skipped = 0
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Ingredients"):
            # Check if ingredient already exists
            try:
                existing = Ingredient.nodes.get(ingredient_id=row['ingredient_id'])
                skipped += 1
                continue
            except Ingredient.DoesNotExist:
                pass
            
            ingredient = Ingredient(
                ingredient_id=row['ingredient_id'],
                name=row['name'],
                category=row['category'] if pd.notna(row['category']) else 'Unknown',
                calories_per_100g=int(row['calories_per_100g']) if pd.notna(row['calories_per_100g']) else 0,
                kj_per_100g=int(row['kj_per_100g']) if pd.notna(row['kj_per_100g']) else 0
            )
            ingredients.append(ingredient)
            
            if len(ingredients) >= self.batch_size:
                self.save_batch(ingredients)
                created += len(ingredients)
                ingredients = []
        
        if ingredients:
            self.save_batch(ingredients)
            created += len(ingredients)
        
        self.stdout.write(
            self.style.SUCCESS(f'Imported {created} ingredients, skipped {skipped} duplicates')
        )

    def import_recipes(self):
        """Import recipes from CSV"""
        self.stdout.write('Importing recipes...')
        
        csv_path = self.get_csv_path('final_recipes.csv')
        df = pd.read_csv(csv_path)
        
        recipes = []
        created = 0
        skipped = 0
        
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Recipes"):
            # Check if recipe already exists
            try:
                existing = Recipe.nodes.get(recipe_id=row['recipe_id'])
                skipped += 1
                continue
            except Recipe.DoesNotExist:
                pass
            
            recipe = Recipe(
                recipe_id=row['recipe_id'],
                title=row['title'] if pd.notna(row['title']) else '',
                rating=float(row['rating']) if pd.notna(row['rating']) else 0.0,
                calories=float(row['calories']) if pd.notna(row['calories']) else 0.0,
                protein=float(row['protein']) if pd.notna(row['protein']) else 0.0,
                fat=float(row['fat']) if pd.notna(row['fat']) else 0.0,
                sodium=float(row['sodium']) if pd.notna(row['sodium']) else 0.0,
                description=row['description'] if pd.notna(row['description']) else '',
                directions=row['directions'] if pd.notna(row['directions']) else '',
                ingredients_raw=row['ingredients_raw'] if pd.notna(row['ingredients_raw']) else ''
            )
            recipes.append(recipe)
            
            if len(recipes) >= self.batch_size:
                self.save_batch(recipes)
                created += len(recipes)
                recipes = []
        
        if recipes:
            self.save_batch(recipes)
            created += len(recipes)
        
        self.stdout.write(
            self.style.SUCCESS(f'Imported {created} recipes, skipped {skipped} duplicates')
        )

    def import_relationships(self):
        """Import relationships from CSV files"""
        self.stdout.write('Creating relationships...')
        
        # Recipe-Ingredient relationships
        self.create_recipe_ingredient_relationships()
        
        # Recipe-Category relationships
        self.create_recipe_category_relationships()
        
        # Ingredient-Category relationships
        self.create_ingredient_category_relationships()

    def create_recipe_ingredient_relationships(self):
        """Create Recipe-Ingredient CONTAINS relationships"""
        self.stdout.write('Creating Recipe-Ingredient relationships...')
        
        csv_path = self.get_csv_path('final_recipe_ingredient_rels.csv')
        df = pd.read_csv(csv_path)
        
        created = 0
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Recipe-Ingredient"):
            try:
                recipe = Recipe.nodes.get(recipe_id=row['recipe_id'])
                ingredient = Ingredient.nodes.get(ingredient_id=row['ingredient_id'])
                
                if not recipe.contains.is_connected(ingredient):
                    recipe.contains.connect(ingredient)
                    created += 1
                    
            except (Recipe.DoesNotExist, Ingredient.DoesNotExist):
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created} Recipe-Ingredient relationships')
        )

    def create_recipe_category_relationships(self):
        """Create Recipe-Category BELONGS_TO relationships"""
        self.stdout.write('Creating Recipe-Category relationships...')
        
        csv_path = self.get_csv_path('final_recipe_category_rels.csv')
        df = pd.read_csv(csv_path)
        
        created = 0
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Recipe-Category"):
            try:
                recipe = Recipe.nodes.get(recipe_id=row['recipe_id'])
                category = Category.nodes.get(category_id=row['category_id'])
                
                if not recipe.belongs_to.is_connected(category):
                    recipe.belongs_to.connect(category)
                    created += 1
                    
            except (Recipe.DoesNotExist, Category.DoesNotExist):
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created} Recipe-Category relationships')
        )

    def create_ingredient_category_relationships(self):
        """Create Ingredient-Category CLASSIFIED_AS relationships"""
        self.stdout.write('Creating Ingredient-Category relationships...')
        
        csv_path = self.get_csv_path('final_ingredient_category_rels.csv')
        df = pd.read_csv(csv_path)
        
        created = 0
        for _, row in tqdm(df.iterrows(), total=len(df), desc="Ingredient-Category"):
            try:
                ingredient = Ingredient.nodes.get(ingredient_id=row['ingredient_id'])
                category = Category.nodes.get(category_id=row['category_id'])
                
                if not ingredient.classified_as.is_connected(category):
                    ingredient.classified_as.connect(category)
                    created += 1
                    
            except (Ingredient.DoesNotExist, Category.DoesNotExist):
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created} Ingredient-Category relationships')
        )

    def save_batch(self, objects):
        """Save batch of objects to Neo4j"""
        for obj in objects:
            obj.save()