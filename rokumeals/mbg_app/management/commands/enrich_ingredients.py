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

from rokumeals.mbg_app.models import Ingredient
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
            '--batch-delay',
            type=float,
            default=1.0,
            help='Delay between requests in seconds (default: 1.0)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-enrich ingredients that already have DBpedia data'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Starting DBpedia ingredient enrichment...')
        )
        
        # Initialize enricher
        enricher = DBpediaEnricher()
        
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
        success_count = 0
        error_count = 0
        enriched_count = 0
        
        for i, ingredient in enumerate(ingredients_to_process, 1):
            self.stdout.write(
                f"\n[{i}/{len(ingredients_to_process)}] Processing: {ingredient.name}"
            )
            
            try:
                # Check if already enriched (unless force is used)
                if not options['force'] and hasattr(ingredient, 'dbpedia_uri') and ingredient.dbpedia_uri:
                    self.stdout.write(
                        self.style.WARNING(f"  ⏭️  Already enriched (use --force to re-enrich)")
                    )
                    continue
                
                # Get enrichment data from DBpedia
                enriched_data = enricher.enrich_ingredient(ingredient.name)
                
                if enriched_data:
                    if options['dry_run']:
                        self.stdout.write(
                            self.style.SUCCESS(f"  🔍 DRY RUN: Would enrich with {len(enriched_data)} properties")
                        )
                        self._display_enrichment_preview(enriched_data)
                    else:
                        # Update ingredient in Neo4j
                        self._update_ingredient_with_enrichment(ingredient, enriched_data)
                        enriched_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✅ Enriched with {len(enriched_data)} properties")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ❌ No enrichment data found")
                    )
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  💥 Error: {str(e)}")
                )
                logger.error(f"Error processing ingredient {ingredient.name}: {str(e)}")
            
            # Rate limiting
            if options['batch_delay'] > 0 and i < len(ingredients_to_process):
                import time
                time.sleep(options['batch_delay'])
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Enrichment completed!\n"
                f"   Successfully processed: {success_count}\n"
                f"   Actually enriched: {enriched_count}\n"
                f"   Errors: {error_count}"
            )
        )
    
    def _get_ingredients_to_process(self, options) -> List[Ingredient]:
        """Get list of ingredients to process based on command options"""
        
        if options['ingredient']:
            # Process specific ingredient
            try:
                ingredient = Ingredient.nodes.get(name__icontains=options['ingredient'])
                return [ingredient]
            except Ingredient.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Ingredient '{options['ingredient']}' not found")
                )
                return []
            except Exception as e:
                # Multiple matches - get first one
                ingredients = Ingredient.nodes.filter(name__icontains=options['ingredient'])[:1]
                return list(ingredients)
        
        else:
            # Get all ingredients or limited set
            query = Ingredient.nodes.all()
            
            if options['limit']:
                query = query[:options['limit']]
            
            return list(query)
    
    def _update_ingredient_with_enrichment(self, ingredient: Ingredient, enriched_data: Dict):
        """Update ingredient node with enriched data"""
        
        # Map enriched data to ingredient properties
        for key, value in enriched_data.items():
            if hasattr(ingredient, key) or key.startswith('dbpedia_') or key.endswith('_at'):
                setattr(ingredient, key, value)
        
        # Save the updated ingredient
        ingredient.save()
    
    def _display_enrichment_preview(self, enriched_data: Dict):
        """Display preview of enrichment data for dry run"""
        for key, value in enriched_data.items():
            self.stdout.write(f"    {key}: {value}")