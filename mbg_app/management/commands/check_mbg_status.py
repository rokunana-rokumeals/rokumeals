"""
Django Management Command untuk check status MBG database di Neo4j
Usage: python manage.py check_mbg_status
"""
from django.core.management.base import BaseCommand
from neomodel import db

from mbg_app.models import Recipe, Ingredient, Category


class Command(BaseCommand):
    help = 'Check MBG database status in Neo4j'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Checking MBG database status...')
        )
        
        try:
            # Get basic counts
            recipe_count = len(Recipe.nodes.all())
            ingredient_count = len(Ingredient.nodes.all())
            category_count = len(Category.nodes.all())
            
            # Get relationship counts
            recipe_ingredient_count = self.get_relationship_count('CONTAINS')
            recipe_category_count = self.get_relationship_count('BELONGS_TO') 
            ingredient_category_count = self.get_relationship_count('CLASSIFIED_AS')
            
            self.stdout.write('\n=== MBG DATABASE STATUS ===')
            self.stdout.write(f'📖 Recipes: {recipe_count:,}')
            self.stdout.write(f'🥗 Ingredients: {ingredient_count:,}')
            self.stdout.write(f'📁 Categories: {category_count:,}')
            self.stdout.write('')
            self.stdout.write('=== RELATIONSHIPS ===')
            self.stdout.write(f'🔗 Recipe-Ingredient (CONTAINS): {recipe_ingredient_count:,}')
            self.stdout.write(f'🔗 Recipe-Category (BELONGS_TO): {recipe_category_count:,}')
            self.stdout.write(f'🔗 Ingredient-Category (CLASSIFIED_AS): {ingredient_category_count:,}')
            
            if options['detailed']:
                self.show_detailed_stats()
            
            # Check if data exists
            if recipe_count == 0 and ingredient_count == 0:
                self.stdout.write(
                    self.style.WARNING('\n❌ No data found! Run: python manage.py import_mbg_data')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('\n✅ Database has data and is ready!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error checking database status: {str(e)}')
            )

    def get_relationship_count(self, rel_type):
        """Get count of specific relationship type"""
        try:
            result = db.cypher_query(
                f"MATCH ()-[r:{rel_type}]->() RETURN COUNT(r) as count"
            )
            return result[0][0][0] if result[0] else 0
        except:
            return 0

    def show_detailed_stats(self):
        """Show detailed database statistics"""
        self.stdout.write('\n=== DETAILED STATISTICS ===')
        
        try:
            # Top rated recipes
            top_recipes = Recipe.nodes.filter(rating__gt=0).order_by('-rating')[:5]
            if top_recipes:
                self.stdout.write('\n🌟 Top 5 Rated Recipes:')
                for i, recipe in enumerate(top_recipes, 1):
                    self.stdout.write(f'  {i}. {recipe.title} ({recipe.rating}⭐)')
            
            # Categories distribution
            recipe_categories = Category.nodes.filter(type='recipe')[:10]
            if recipe_categories:
                self.stdout.write('\n📁 Recipe Categories (top 10):')
                for cat in recipe_categories:
                    count = len(cat.has_recipes.all())
                    self.stdout.write(f'  • {cat.name}: {count} recipes')
            
            # Ingredient categories
            ingredient_categories = Category.nodes.filter(type='ingredient')[:10] 
            if ingredient_categories:
                self.stdout.write('\n🥗 Ingredient Categories (top 10):')
                for cat in ingredient_categories:
                    count = len(cat.has_ingredients.all())
                    self.stdout.write(f'  • {cat.name}: {count} ingredients')
                    
        except Exception as e:
            self.stdout.write(f'Error getting detailed stats: {str(e)}')