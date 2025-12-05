from django.core.management.base import BaseCommand
from neomodel import db
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Normalize ingredient names with case differences and fix categories'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
        parser.add_argument('--auto-confirm', action='store_true', help='Skip confirmation prompts')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Starting ingredient normalization...'))
        
        dry_run = options['dry_run']
        auto_confirm = options['auto_confirm']
        
        # Step 1: Find case duplicate ingredients
        duplicates = self.find_case_duplicates()
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('✅ No case duplicates found!'))
            return
            
        self.stdout.write(f'Found {len(duplicates)} groups of case duplicates:')
        
        updates_needed = []
        
        for group in duplicates:
            self.stdout.write(f'\n📋 Duplicate group:')
            
            # Find the best candidate (has proper category and not Unknown)
            best_candidate = None
            to_update = []
            
            for item in group:
                name, category, ing_id = item
                self.stdout.write(f'  - "{name}" (category: {category}, ID: {ing_id[:8]}...)')
                
                if category and category != 'Unknown' and category != '':
                    if not best_candidate:
                        best_candidate = item
                else:
                    to_update.append(item)
            
            if best_candidate and to_update:
                best_name, best_category, best_id = best_candidate
                self.stdout.write(f'  ✅ Best candidate: "{best_name}" with category: {best_category}')
                
                for item in to_update:
                    name, category, ing_id = item
                    updates_needed.append({
                        'id': ing_id,
                        'current_name': name,
                        'new_name': best_name,
                        'current_category': category,
                        'new_category': best_category
                    })
                    self.stdout.write(f'  🔄 Will update: "{name}" → "{best_name}" (category: {category} → {best_category})')
        
        if not updates_needed:
            self.stdout.write(self.style.WARNING('No updates needed - all duplicates already have proper categories'))
            return
            
        self.stdout.write(f'\n📊 Summary: {len(updates_needed)} ingredients need updating')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - No changes will be made'))
            return
            
        if not auto_confirm:
            confirm = input('\nProceed with updates? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return
        
        # Execute updates
        self.stdout.write('\n🚀 Executing updates...')
        
        success_count = 0
        for update in updates_needed:
            try:
                query = """
                MATCH (i:Ingredient {ingredient_id: $ing_id})
                SET i.name = $new_name, i.category = $new_category
                RETURN i.name as updated_name
                """
                
                result, meta = db.cypher_query(query, {
                    'ing_id': update['id'],
                    'new_name': update['new_name'],
                    'new_category': update['new_category']
                })
                
                if result:
                    success_count += 1
                    self.stdout.write(f'  ✅ Updated: {update["current_name"]} → {update["new_name"]}')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Failed to update {update["current_name"]}: {str(e)}')
        
        self.stdout.write(f'\n🎉 Successfully updated {success_count}/{len(updates_needed)} ingredients')
        self.stdout.write(self.style.SUCCESS('✨ Normalization complete!'))

    def find_case_duplicates(self):
        """Find ingredients with same name but different cases"""
        query = """
        MATCH (i:Ingredient)
        WITH toLower(i.name) as lower_name, collect({name: i.name, category: i.category, id: i.ingredient_id}) as ingredients
        WHERE size(ingredients) > 1
        RETURN lower_name, ingredients
        ORDER BY lower_name
        """
        
        try:
            results, meta = db.cypher_query(query)
            duplicates = []
            
            for row in results:
                lower_name, ingredients = row
                # Convert to list of tuples
                group = [(ing['name'], ing['category'], ing['id']) for ing in ingredients]
                duplicates.append(group)
                
            return duplicates
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error finding duplicates: {str(e)}'))
            return []