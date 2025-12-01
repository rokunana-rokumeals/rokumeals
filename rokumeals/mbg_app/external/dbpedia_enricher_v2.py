"""
DBpedia SPARQL Integration for Ingredient Nutritional Enrichment
================================================================

This module queries DBpedia to enrich ingredient data with additional nutritional information.
DBpedia contains structured data about food items including vitamins, minerals, and nutritional facts.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DBpediaEnricher:
    """
    Enriches ingredient data using DBpedia SPARQL endpoint
    """
    
    def __init__(self):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)
    
    def clean_ingredient_name(self, ingredient_name: str) -> str:
        """
        Clean ingredient name for DBpedia searching
        """
        # Remove common cooking terms
        clean_name = ingredient_name.lower()
        
        # Remove measure words and common cooking terms
        remove_terms = [
            'fresh', 'dried', 'chopped', 'sliced', 'diced', 'minced',
            'ground', 'whole', 'raw', 'cooked', 'organic', 'extra',
            'virgin', 'unsalted', 'salted', 'low', 'fat', 'sodium',
            'cup', 'cups', 'tablespoon', 'tablespoons', 'teaspoon', 'teaspoons',
            'pound', 'pounds', 'ounce', 'ounces', 'gram', 'grams', 'kg'
        ]
        
        for term in remove_terms:
            clean_name = re.sub(rf'\b{term}\b', '', clean_name)
        
        # Clean up extra spaces and punctuation
        clean_name = re.sub(r'[^\w\s]', '', clean_name)
        clean_name = ' '.join(clean_name.split())
        
        return clean_name.strip()

    def search_ingredient_in_dbpedia(self, ingredient_name: str) -> Optional[str]:
        """
        Search for ingredient in DBpedia and return resource URI if found
        """
        clean_name = self.clean_ingredient_name(ingredient_name)
        
        # Try different name variations
        variations = [
            clean_name.title(),          # Tomato
            clean_name.lower(),          # tomato  
            clean_name.capitalize(),     # Tomato
            ingredient_name.title(),     # Original with title case
        ]
        
        for name_variant in variations:
            resource_uri = f"http://dbpedia.org/resource/{name_variant.replace(' ', '_')}"
            
            # Check if resource exists
            check_query = f"""
            ASK WHERE {{
                <{resource_uri}> ?p ?o .
            }}
            """
            
            try:
                self.sparql.setQuery(check_query)
                result = self.sparql.query().convert()
                
                if result.get('boolean', False):
                    logger.info(f"Found DBpedia resource for '{ingredient_name}': {resource_uri}")
                    return resource_uri
                    
            except Exception as e:
                logger.debug(f"Error checking resource {resource_uri}: {e}")
                continue
        
        # If direct resource lookup fails, try search
        try:
            search_query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?resource WHERE {{
                ?resource rdfs:label ?label .
                FILTER (lang(?label) = 'en')
                FILTER (CONTAINS(LCASE(?label), "{clean_name.lower()}"))
            }}
            LIMIT 5
            """
            
            self.sparql.setQuery(search_query)
            result = self.sparql.query().convert()
            
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                resource_uri = bindings[0]['resource']['value']
                logger.info(f"Found DBpedia resource via search for '{ingredient_name}': {resource_uri}")
                return resource_uri
                
        except Exception as e:
            logger.error(f"Error searching DBpedia for '{ingredient_name}': {e}")
        
        logger.info(f"No DBpedia resource found for ingredient: {ingredient_name}")
        return None

    def get_nutritional_data(self, resource_uri: str) -> Dict:
        """
        Get nutritional information for a DBpedia resource
        Based on actual properties found in DBpedia
        """
        try:
            # Get resource name from URI
            resource_name = resource_uri.split('/')[-1]
            
            query = f"""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dbr: <http://dbpedia.org/resource/>
            PREFIX dbp: <http://dbpedia.org/property/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?abstract ?carbs ?protein ?fat ?calories ?fiber ?vitaminC ?calcium ?iron ?water
            WHERE {{
                dbr:{resource_name} dbo:abstract ?abstract .
                FILTER (lang(?abstract) = 'en')
                
                OPTIONAL {{ dbr:{resource_name} dbp:carbs ?carbs . }}
                OPTIONAL {{ dbr:{resource_name} dbp:protein ?protein . }}
                OPTIONAL {{ dbr:{resource_name} dbp:fat ?fat . }}
                OPTIONAL {{ dbr:{resource_name} dbp:kcal ?calories . }}
                OPTIONAL {{ dbr:{resource_name} dbp:fiber ?fiber . }}
                OPTIONAL {{ dbr:{resource_name} dbp:vitc ?vitaminC . }}
                OPTIONAL {{ dbr:{resource_name} dbp:calcium ?calcium . }}
                OPTIONAL {{ dbr:{resource_name} dbp:iron ?iron . }}
                OPTIONAL {{ dbr:{resource_name} dbp:water ?water . }}
            }}
            """
            
            self.sparql.setQuery(query)
            result = self.sparql.query().convert()
            
            nutritional_data = {}
            
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                binding = bindings[0]
                
                # Extract abstract
                if 'abstract' in binding:
                    abstract = binding['abstract']['value']
                    nutritional_data['description'] = abstract[:500] + "..." if len(abstract) > 500 else abstract
                
                # Extract nutritional values
                nutritional_fields = {
                    'carbs': 'carbohydrates_g',
                    'protein': 'protein_g', 
                    'fat': 'fat_g',
                    'calories': 'calories_per_100g',
                    'fiber': 'fiber_g',
                    'vitaminC': 'vitamin_c_mg',
                    'calcium': 'calcium_mg',
                    'iron': 'iron_mg',
                    'water': 'water_g'
                }
                
                for dbp_field, our_field in nutritional_fields.items():
                    if dbp_field in binding and binding[dbp_field]:
                        value_str = binding[dbp_field]['value']
                        numeric_value = self._extract_numeric_value(value_str)
                        if numeric_value is not None:
                            nutritional_data[our_field] = numeric_value
                
                nutritional_data['dbpedia_resource'] = resource_uri
                
            return nutritional_data
            
        except Exception as e:
            logger.error(f"Error getting nutritional data from {resource_uri}: {e}")
            return {}

    def _extract_numeric_value(self, value_str: str) -> Optional[float]:
        """
        Extract numeric value from DBpedia property value
        """
        if not value_str:
            return None
            
        try:
            # Remove common units and extract number
            clean_value = re.sub(r'[^\d\.]', '', str(value_str))
            if clean_value:
                return float(clean_value)
        except (ValueError, TypeError):
            pass
        
        return None

    def enrich_ingredient(self, ingredient_name: str) -> Dict:
        """
        Main method to enrich an ingredient with DBpedia data
        """
        try:
            # Search for ingredient in DBpedia
            resource_uri = self.search_ingredient_in_dbpedia(ingredient_name)
            
            if not resource_uri:
                return {
                    'ingredient_name': ingredient_name,
                    'dbpedia_found': False,
                    'error': 'No DBpedia resource found'
                }
            
            # Get nutritional data
            nutritional_data = self.get_nutritional_data(resource_uri)
            
            result = {
                'ingredient_name': ingredient_name,
                'dbpedia_found': True,
                'dbpedia_resource': resource_uri,
                **nutritional_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching ingredient '{ingredient_name}': {e}")
            return {
                'ingredient_name': ingredient_name,
                'dbpedia_found': False,
                'error': str(e)
            }


# Test function untuk coba langsung
def test_enricher():
    enricher = DBpediaEnricher()
    
    # Test dengan beberapa ingredient
    test_ingredients = ["tomato", "rice", "apple", "potato", "carrot"]
    
    for ingredient in test_ingredients:
        print(f"\n{'='*50}")
        print(f"Testing: {ingredient}")
        print('='*50)
        
        result = enricher.enrich_ingredient(ingredient)
        
        if result['dbpedia_found']:
            print(f"✅ Found data for {ingredient}")
            print(f"Resource: {result.get('dbpedia_resource', 'N/A')}")
            
            # Print nutritional data
            nutritional_keys = ['calories_per_100g', 'carbohydrates_g', 'protein_g', 'fat_g', 'fiber_g']
            for key in nutritional_keys:
                if key in result:
                    print(f"{key}: {result[key]}")
            
            if 'description' in result:
                print(f"Description: {result['description'][:200]}...")
        else:
            print(f"❌ No data found for {ingredient}")
            print(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    test_enricher()