import json
import csv
from django.core.management.base import BaseCommand
from mbg_app.models import Recipe, Ingredient, Category

class Command(BaseCommand):
    help = 'Import embeddings from external generation'

    def add_arguments(self, parser):
        parser.add_argument('--format', choices=['json', 'csv'], default='json')
        parser.add_argument('--input-dir', default='embedding_data')
        parser.add_argument('--embedding-file', required=True, help='File containing embeddings')
        parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')

    def handle(self, *args, **options):
        embedding_file = options['embedding_file']
        
        # Load embeddings
        embeddings_data = self._load_embeddings(embedding_file, options['format'])
        
        # Create lookup dictionary
        embeddings_lookup = {}
        for item in embeddings_data:
            key = f"{item['type']}_{item['id']}"
            embeddings_lookup[key] = item['embedding']
        
        updated_count = 0
        skipped_count = 0
        
        # Update Recipes
        recipe_updates = 0
        for recipe in Recipe.objects.all():
            key = f"recipe_{recipe.id}"
            if key in embeddings_lookup:
                if not options['dry_run']:
                    recipe.embedding = json.dumps(embeddings_lookup[key])
                    recipe.save()
                recipe_updates += 1
            else:
                skipped_count += 1
        
        # Update Ingredients
        ingredient_updates = 0
        for ingredient in Ingredient.objects.all():
            key = f"ingredient_{ingredient.id}"
            if key in embeddings_lookup:
                if not options['dry_run']:
                    ingredient.embedding = json.dumps(embeddings_lookup[key])
                    ingredient.save()
                ingredient_updates += 1
            else:
                skipped_count += 1
        
        # Update Categories
        category_updates = 0
        for category in Category.objects.all():
            key = f"category_{category.id}"
            if key in embeddings_lookup:
                if not options['dry_run']:
                    category.embedding = json.dumps(embeddings_lookup[key])
                    category.save()
                category_updates += 1
            else:
                skipped_count += 1
        
        updated_count = recipe_updates + ingredient_updates + category_updates
        
        status = "DRY RUN - " if options['dry_run'] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f'{status}Successfully imported embeddings:\n'
                f'- {recipe_updates} recipes updated\n'
                f'- {ingredient_updates} ingredients updated\n'
                f'- {category_updates} categories updated\n'
                f'- {skipped_count} items skipped (no embedding found)\n'
                f'Total: {updated_count} items updated'
            )
        )

    def _load_embeddings(self, file_path, format_type):
        """Load embeddings from file"""
        if format_type == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            embeddings = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse embedding from string representation
                    embedding_str = row['embedding']
                    if embedding_str.startswith('[') and embedding_str.endswith(']'):
                        embedding = json.loads(embedding_str)
                    else:
                        # Handle comma-separated values
                        embedding = [float(x.strip()) for x in embedding_str.split(',')]
                    
                    embeddings.append({
                        'id': row['id'],
                        'type': row['type'],
                        'embedding': embedding
                    })
            return embeddings