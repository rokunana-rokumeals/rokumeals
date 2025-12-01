"""
Django Management Command: Enrich Ingredients with DBpedia Data
=============================================================

This command enriches existing ingredients in the Neo4j database with 
additional nutritional information from DBpedia.

Usage:
    python manage.py enrich_ingredients
    python manage.py enrich_ingredients --limit 10
    python manage.py enrich_ingredients --ingredient "tomato"
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging
import json
from typing import List, Dict
import sys
import os

# Add the project root to Python path to import our enricher
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from mbg_app.models import Ingredient
from rokumeals.mbg_app.external.dbpedia_enricher_v2 import DBpediaEnricher

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Enrich ingredients with nutritional data from DBpedia'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of ingredients to process'
        )
        
        parser.add_argument(
            '--ingredient',
            type=str,
            help='Enrich specific ingredient by name'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be enriched without saving changes'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Starting DBpedia ingredient enrichment...')
        )
        
        # Initialize enricher
        try:
            enricher = DBpediaEnricher()
        except Exception as e:
            raise CommandError(f"Failed to initialize DBpedia enricher: {e}")
        
        # Get ingredients to process
        ingredients_to_process = self._get_ingredients_to_process(options)
        
        if not ingredients_to_process:
            self.stdout.write(
                self.style.WARNING('No ingredients found to process.')
            )
            return
        
        self.stdout.write(
            f"📊 Found {len(ingredients_to_process)} ingredients to process"
        )
        
        # Process ingredients
        successful_enrichments = 0
        failed_enrichments = 0
        
        for i, ingredient in enumerate(ingredients_to_process, 1):
            self.stdout.write(f"\n[{i}/{len(ingredients_to_process)}] Processing: {ingredient.name}")
            
            try:
                # Enrich ingredient
                enrichment_result = enricher.enrich_ingredient(ingredient.name)
                
                if enrichment_result['dbpedia_found']:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✅ Found DBpedia data")
                    )
                    
                    # Print found data
                    if 'dbpedia_resource' in enrichment_result:
                        self.stdout.write(f"  Resource: {enrichment_result['dbpedia_resource']}")
                    
                    nutritional_info = []
                    for key, value in enrichment_result.items():
                        if key.endswith('_g') or key.endswith('_mg') or 'calories' in key:
                            nutritional_info.append(f"{key}: {value}")
                    
                    if nutritional_info:
                        self.stdout.write(f"  Nutrition: {', '.join(nutritional_info[:3])}")
                    
                    # Update ingredient if not dry run
                    if not options['dry_run']:
                        self._update_ingredient(ingredient, enrichment_result)
                        self.stdout.write("  💾 Updated ingredient in database")
                    else:
                        self.stdout.write("  🏃 DRY RUN: Would update ingredient")
                    
                    successful_enrichments += 1
                    
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ❌ No DBpedia data found")
                    )
                    if 'error' in enrichment_result:
                        self.stdout.write(f"  Error: {enrichment_result['error']}")
                    failed_enrichments += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  💥 Error processing {ingredient.name}: {e}")
                )
                failed_enrichments += 1
            
            # Add small delay to be nice to DBpedia
            import time
            time.sleep(0.5)
        
        # Summary
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(
            self.style.SUCCESS(
                f"🎉 Enrichment complete!\n"
                f"   ✅ Successful: {successful_enrichments}\n"
                f"   ❌ Failed: {failed_enrichments}\n"
                f"   📊 Total processed: {len(ingredients_to_process)}"
            )
        )
    
    def _get_ingredients_to_process(self, options) -> List:
        """Get list of ingredients to process based on options"""
        try:
            if options['ingredient']:
                # Process specific ingredient
                ingredients = Ingredient.nodes.filter(name__icontains=options['ingredient'])
                return list(ingredients)
            else:
                # Process all ingredients (with limit)
                if options['limit']:
                    return list(Ingredient.nodes.all()[:options['limit']])
                else:
                    return list(Ingredient.nodes.all())
        except Exception as e:
            raise CommandError(f"Failed to get ingredients from database: {e}")
    
    def _update_ingredient(self, ingredient, enrichment_data):
        """Update ingredient with enriched data"""
        try:
            # Update nutritional fields
            nutritional_fields = {
                'calories_per_100g': 'calories_per_100g',
                'carbohydrates_g': 'carbohydrates_g',
                'protein_g': 'protein_g',
                'fat_g': 'fat_g',
                'fiber_g': 'fiber_g',
                'vitamin_c_mg': 'vitamin_c_mg',
                'calcium_mg': 'calcium_mg',
                'iron_mg': 'iron_mg',
                'water_g': 'water_g'
            }
            
            updated_fields = []
            for source_field, target_field in nutritional_fields.items():
                if source_field in enrichment_data and enrichment_data[source_field]:
                    setattr(ingredient, target_field, enrichment_data[source_field])
                    updated_fields.append(target_field)
            
            # Update other fields
            if 'description' in enrichment_data:
                ingredient.description = enrichment_data['description'][:500]
                updated_fields.append('description')
            
            if 'dbpedia_resource' in enrichment_data:
                ingredient.dbpedia_resource = enrichment_data['dbpedia_resource']
                updated_fields.append('dbpedia_resource')
            
            # Save changes
            ingredient.save()
            
            logger.info(f"Updated ingredient '{ingredient.name}' with fields: {updated_fields}")
            
        except Exception as e:
            logger.error(f"Failed to update ingredient '{ingredient.name}': {e}")
            raise