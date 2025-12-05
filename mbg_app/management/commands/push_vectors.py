import json
import os
from django.core.management.base import BaseCommand
from neomodel import db
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Push Qwen embeddings to Neo4j Aura Vector Index'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', 
            type=str, 
            required=True,
            help='Path to the JSON file (e.g., embeddings_output/embeddings_recipes.json)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for Neo4j transactions'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        batch_size = options['batch_size']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        self.stdout.write(f"Loading JSON from {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 1. CLEAN AND PREPARE DATA
        self.stdout.write("Filtering and preparing batches...")
        
        clean_batches = {
            'recipe': [],
            'ingredient': [],
            'category': []
        }
        
        skipped_none = 0
        
        for item in data:
            # SKIP if ID is None (Fixes the issue in your screenshot)
            # if str(item.get('id')) == "None" or not item.get('id'):
            #     skipped_none += 1
            #     continue
                
            # SKIP if embedding is missing/empty
            if not item.get('embedding'):
                continue

            node_type = item.get('type', '').lower()
            
            # Add to appropriate list
            if node_type in clean_batches:
                clean_batches[node_type].append({
                    'id': str(item['id']), # Ensure ID is string
                    'vector': item['embedding']
                })

        self.stdout.write(f"Skipped {skipped_none} items with ID='None'")

        # 2. PUSH TO NEO4J
        for node_type, items in clean_batches.items():
            if not items:
                continue

            self.stdout.write(self.style.SUCCESS(f"\nPushing {len(items)} {node_type} vectors to Neo4j..."))

            # Configuration based on type
            if node_type == 'recipe':
                label = 'Recipe'
                id_field = 'recipe_id'
            elif node_type == 'ingredient':
                label = 'Ingredient'
                id_field = 'ingredient_id'
            elif node_type == 'category':
                label = 'Category'
                id_field = 'category_id'
            
            # The Cypher Query using UNWIND for high performance
            query = f"""
            UNWIND $batch AS row
            MATCH (n:{label} {{{id_field}: row.id}})
            SET n.embedding = row.vector
            RETURN count(n) as updated
            """

            total_updated = 0
            
            # Process in chunks
            with tqdm(total=len(items)) as pbar:
                for i in range(0, len(items), batch_size):
                    batch = items[i:i+batch_size]
                    
                    try:
                        results, _ = db.cypher_query(query, {'batch': batch})
                        # results is [[count]]
                        if results:
                            total_updated += results[0][0]
                        pbar.update(len(batch))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Batch error: {e}"))

            self.stdout.write(f"Updated {total_updated} {node_type} nodes.")

        self.stdout.write(self.style.SUCCESS("\nSync Complete!"))