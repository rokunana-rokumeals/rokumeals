"""
Django Management Command: Enrich Ingredients with Wikidata Data
=============================================================

This command enriches existing ingredients in the Neo4j database with 
additional nutritional information from Wikidata.

Usage:
    python manage.py enrich_ingredients_wikidata
    python manage.py enrich_ingredients_wikidata --limit 10
    python manage.py enrich_ingredients_wikidata --ingredient "tomato"
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
from rokumeals.mbg_app.external.wikidata_enricher import WikidataEnricher

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Enrich ingredients with nutritional data from Wikidata'
    
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
            self.style.SUCCESS('🔍 Starting Wikidata ingredient enrichment...')
        )
        
        # Initialize enricher
        try:
            enricher = WikidataEnricher()
        except Exception as e:
            raise CommandError(f"Failed to initialize Wikidata enricher: {e}")
        
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
                enrichment_result = enricher.enrich(ingredient.name)
                
                if enrichment_result['found']:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✅ Found Wikidata data")
                    )
                    
                    # Print found data
                    if 'label' in enrichment_result:
                        self.stdout.write(f"  Entity: {enrichment_result['label']}")
                    if 'uri' in enrichment_result:
                        self.stdout.write(f"  URI: {enrichment_result['uri']}")
                    if 'description' in enrichment_result:
                        self.stdout.write(f"  Description: {enrichment_result['description'][:100]}...")
                    
                    # Show available attributes
                    attributes = enrichment_result.get('attributes', {})
                    if attributes:
                        self.stdout.write(f"  Found {len(attributes)} attributes:")
                        for attr_name in list(attributes.keys())[:5]:  # Show first 5
                            self.stdout.write(f"    - {attr_name}: {attributes[attr_name][:50]}...")
                    
                    # Update ingredient if not dry run
                    if not options['dry_run']:
                        self._update_ingredient(ingredient, enrichment_result)
                        self.stdout.write("  💾 Updated ingredient in database")
                    else:
                        self.stdout.write("  🏃 DRY RUN: Would update ingredient")
                    
                    successful_enrichments += 1
                    
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ❌ No Wikidata data found")
                    )
                    self.stdout.write(f"  Searched for: '{enrichment_result.get('clean_name', ingredient.name)}'")
                    failed_enrichments += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  💥 Error processing {ingredient.name}: {e}")
                )
                failed_enrichments += 1
            
            # Add small delay to be nice to Wikidata
            import time
            time.sleep(0.2)  # Wikidata is faster, shorter delay
        
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
            updated_fields = []
            attributes = enrichment_data.get('attributes', {})
            
            # Map common nutritional attributes from Wikidata to our fields
            nutritional_mapping = {
                'energy per unit mass': 'calories_per_100g',
                'carbohydrate': 'carbohydrates_g',
                'protein': 'protein_g',
                'fat': 'fat_g',
                'dietary fiber': 'fiber_g',
                'sugar': 'sugar_g',
                'water': 'water_g',
                'vitamin C': 'vitamin_c_mg',
                'calcium': 'calcium_mg',
                'iron': 'iron_mg',
                'sodium': 'sodium_mg',
                'potassium': 'potassium_mg',
                'magnesium': 'magnesium_mg'
            }
            
            # Process nutritional attributes
            import re
            for attr_name, field_name in nutritional_mapping.items():
                if attr_name in attributes:
                    # Extract numeric value from string (e.g., "1.5 gram per 100 gram" -> 1.5)
                    attr_value = attributes[attr_name]
                    numbers = re.findall(r'\d+(?:\.\d+)?', str(attr_value))
                    if numbers:
                        setattr(ingredient, field_name, float(numbers[0]))
                        updated_fields.append(field_name)
            
            # Update other fields
            if 'description' in enrichment_data and enrichment_data['description']:
                ingredient.description = enrichment_data['description'][:500]
                updated_fields.append('description')
            
            if 'image_url' in enrichment_data and enrichment_data['image_url']:
                ingredient.image_url = enrichment_data['image_url']
                updated_fields.append('image_url')
            
            if 'uri' in enrichment_data:
                ingredient.wikidata_entity = enrichment_data['uri']
                updated_fields.append('wikidata_entity')
            
            if 'category' in enrichment_data:
                ingredient.classification = enrichment_data['category']
                updated_fields.append('classification')
            
            # Save changes
            ingredient.save()
            
            logger.info(f"Updated ingredient '{ingredient.name}' with fields: {updated_fields}")
            
        except Exception as e:
            logger.error(f"Failed to update ingredient '{ingredient.name}': {e}")
            raise