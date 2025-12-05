import os
import django
import sys

# Setup Django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rokumeals.settings')
django.setup()

from neomodel import db

def merge_duplicate_ingredients():
    """
    Merge duplicate ingredients by transferring relationships from duplicates to the best candidate
    and then deleting the duplicates.
    """
    print("🔍 Finding duplicate ingredients to merge...")
    
    # Find groups of ingredients with same name (case insensitive) but different IDs
    query = """
    MATCH (i:Ingredient)
    WITH toLower(i.name) as lower_name, collect({
        id: i.ingredient_id,
        name: i.name,
        category: i.category
    }) as ingredients
    WHERE size(ingredients) > 1
    RETURN lower_name, ingredients
    """
    
    results, _ = db.cypher_query(query)
    
    merge_operations = []
    
    for row in results:
        lower_name, ingredients = row
        
        # Find the best candidate (prefer non-Unknown category, then alphabetically first)
        best_candidate = None
        duplicates_to_merge = []
        
        # Sort ingredients: non-Unknown category first, then alphabetically
        sorted_ingredients = sorted(ingredients, key=lambda x: (
            x['category'] == 'Unknown',  # Unknown categories go last
            x['name']  # Then sort alphabetically
        ))
        
        best_candidate = sorted_ingredients[0]
        duplicates_to_merge = sorted_ingredients[1:]
        
        if duplicates_to_merge:
            print(f"\n📋 Found duplicates for '{lower_name}':")
            print(f"  ✅ Keep: {best_candidate['name']} (ID: {best_candidate['id'][:8]}..., Category: {best_candidate['category']})")
            
            for dup in duplicates_to_merge:
                print(f"  🔄 Merge: {dup['name']} (ID: {dup['id'][:8]}..., Category: {dup['category']})")
                
                merge_operations.append({
                    'keep_id': best_candidate['id'],
                    'merge_id': dup['id'],
                    'name': lower_name
                })
    
    if not merge_operations:
        print("✅ No duplicates found to merge!")
        return
    
    print(f"\n📊 Summary: {len(merge_operations)} ingredients need merging")
    
    # Execute merge operations
    success_count = 0
    
    for op in merge_operations:
        try:
            print(f"\n🔄 Merging {op['name']}...")
            
            # Step 1: Transfer all CONTAINS relationships from duplicate to best
            transfer_contains_query = """
            MATCH (duplicate:Ingredient {ingredient_id: $merge_id})<-[r:CONTAINS]-(recipe:Recipe)
            MATCH (keep:Ingredient {ingredient_id: $keep_id})
            
            // Check if relationship already exists
            OPTIONAL MATCH (recipe)-[existing:CONTAINS]->(keep)
            
            // Only create if it doesn't exist
            FOREACH (ignore IN CASE WHEN existing IS NULL THEN [1] ELSE [] END |
                CREATE (recipe)-[:CONTAINS]->(keep)
            )
            
            // Delete old relationship
            DELETE r
            
            RETURN count(r) as transferred_relationships
            """
            
            result1, _ = db.cypher_query(transfer_contains_query, {
                'merge_id': op['merge_id'],
                'keep_id': op['keep_id']
            })
            
            transferred = result1[0][0] if result1 else 0
            print(f"  ✅ Transferred {transferred} recipe relationships")
            
            # Step 2: Transfer CLASSIFIED_AS relationships
            transfer_classified_query = """
            MATCH (duplicate:Ingredient {ingredient_id: $merge_id})-[r:CLASSIFIED_AS]->(category:Category)
            MATCH (keep:Ingredient {ingredient_id: $keep_id})
            
            // Check if relationship already exists
            OPTIONAL MATCH (keep)-[existing:CLASSIFIED_AS]->(category)
            
            // Only create if it doesn't exist
            FOREACH (ignore IN CASE WHEN existing IS NULL THEN [1] ELSE [] END |
                CREATE (keep)-[:CLASSIFIED_AS]->(category)
            )
            
            // Delete old relationship
            DELETE r
            
            RETURN count(r) as transferred_categories
            """
            
            result2, _ = db.cypher_query(transfer_classified_query, {
                'merge_id': op['merge_id'],
                'keep_id': op['keep_id']
            })
            
            transferred_cats = result2[0][0] if result2 else 0
            print(f"  ✅ Transferred {transferred_cats} category relationships")
            
            # Step 3: Transfer embedding if the keep ingredient doesn't have one
            transfer_embedding_query = """
            MATCH (duplicate:Ingredient {ingredient_id: $merge_id})
            MATCH (keep:Ingredient {ingredient_id: $keep_id})
            
            // Only transfer if keep doesn't have embedding and duplicate does
            FOREACH (ignore IN CASE 
                WHEN keep.embedding IS NULL AND duplicate.embedding IS NOT NULL 
                THEN [1] ELSE [] END |
                SET keep.embedding = duplicate.embedding
            )
            
            RETURN CASE 
                WHEN keep.embedding IS NULL AND duplicate.embedding IS NOT NULL 
                THEN 1 ELSE 0 END as embedding_transferred
            """
            
            result3, _ = db.cypher_query(transfer_embedding_query, {
                'merge_id': op['merge_id'],
                'keep_id': op['keep_id']
            })
            
            embedding_transferred = result3[0][0] if result3 else 0
            if embedding_transferred:
                print(f"  ✅ Transferred embedding vector")
            
            # Step 4: Delete the duplicate ingredient
            delete_query = """
            MATCH (duplicate:Ingredient {ingredient_id: $merge_id})
            DELETE duplicate
            RETURN 1 as deleted
            """
            
            result4, _ = db.cypher_query(delete_query, {'merge_id': op['merge_id']})
            
            if result4:
                print(f"  ✅ Deleted duplicate ingredient")
                success_count += 1
            
        except Exception as e:
            print(f"  ❌ Failed to merge {op['name']}: {str(e)}")
    
    print(f"\n🎉 Successfully merged {success_count}/{len(merge_operations)} duplicates")

def verify_absinthe():
    """Verify Absinthe is properly merged"""
    print("\n🔍 Verifying Absinthe after merge...")
    
    query = """
    MATCH (i:Ingredient)
    WHERE toLower(i.name) = 'absinthe'
    OPTIONAL MATCH (i)<-[:CONTAINS]-(r:Recipe)
    RETURN i.ingredient_id as id, i.name as name, i.category as category, 
           count(r) as recipe_count, collect(r.title)[0..3] as sample_recipes
    """
    
    results, _ = db.cypher_query(query)
    
    print(f"Absinthe ingredients found: {len(results)}")
    for row in results:
        ing_id, name, category, recipe_count, sample_recipes = row
        print(f"  - {name} (ID: {ing_id[:8]}..., Category: {category}, Recipes: {recipe_count})")
        if sample_recipes:
            print(f"    Sample recipes: {sample_recipes}")

if __name__ == "__main__":
    merge_duplicate_ingredients()
    verify_absinthe()
    print("\n✨ Duplicate merge complete!")