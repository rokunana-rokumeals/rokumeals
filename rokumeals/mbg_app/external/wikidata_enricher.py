"""
Wikidata SPARQL Integration for Ingredient Nutritional Enrichment
================================================================

This module queries Wikidata to enrich ingredient data with additional nutritional information.
Wikidata has excellent structured data about food items with nutritional properties.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class WikidataEnricher:
    """
    Enriches ingredient data using Wikidata SPARQL endpoint
    """
    
    def __init__(self):
        self.sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.sparql.setReturnFormat(JSON)
        # Set user agent as required by Wikidata
        self.sparql.addCustomHttpHeader("User-Agent", "MBG-Knowledge-Graph/1.0 (https://github.com/poemich/rokumeals)")
    
    def clean_ingredient_name(self, ingredient_name: str) -> str:
        """Clean ingredient name for searching"""
        clean_name = ingredient_name.lower()
        
        # Remove common cooking terms
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

    def search_ingredient_in_wikidata(self, ingredient_name: str) -> Optional[str]:
        """
        Search for ingredient in Wikidata and return entity ID if found
        """
        clean_name = self.clean_ingredient_name(ingredient_name)
        
        # First try exact match with basic food items
        exact_query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
          ?item wdt:P31/wdt:P279* wd:Q2095 .  # instance of food or subclass of food
          ?item rdfs:label ?itemLabel .
          FILTER(LANG(?itemLabel) = "en")
          FILTER(LCASE(?itemLabel) = "{clean_name.lower()}")
          
          # Prefer basic ingredients over dishes/products
          FILTER NOT EXISTS {{ ?item wdt:P527 ?part . }}  # Not a composite dish
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
        }}
        LIMIT 1
        """
        
        try:
            self.sparql.setQuery(exact_query)
            result = self.sparql.query().convert()
            
            bindings = result.get('results', {}).get('bindings', [])
            
            if bindings:
                item_uri = bindings[0]['item']['value']
                item_label = bindings[0]['itemLabel']['value']
                
                logger.info(f"Found exact Wikidata entity for '{ingredient_name}': {item_label} ({item_uri})")
                return item_uri
            
            # If no exact match, try with raw ingredient name
            raw_exact_query = f"""
            SELECT DISTINCT ?item ?itemLabel WHERE {{
              ?item wdt:P31/wdt:P279* wd:Q2095 .  # instance of food
              ?item rdfs:label ?itemLabel .
              FILTER(LANG(?itemLabel) = "en")
              FILTER(LCASE(?itemLabel) = "{ingredient_name.lower()}")
              
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }}
            LIMIT 1
            """
            
            self.sparql.setQuery(raw_exact_query)
            result = self.sparql.query().convert()
            
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                item_uri = bindings[0]['item']['value']
                item_label = bindings[0]['itemLabel']['value']
                logger.info(f"Found raw exact Wikidata entity for '{ingredient_name}': {item_label} ({item_uri})")
                return item_uri
            
            # Last resort: contains search but prioritize single words
            contains_query = f"""
            SELECT DISTINCT ?item ?itemLabel ?description WHERE {{
              ?item wdt:P31/wdt:P279* wd:Q2095 .  # instance of food
              ?item rdfs:label ?itemLabel .
              FILTER(LANG(?itemLabel) = "en")
              FILTER(CONTAINS(LCASE(?itemLabel), "{clean_name.lower()}"))
              
              # Strongly prefer single words (basic ingredients)
              FILTER(STRLEN(?itemLabel) < 20)
              FILTER(!CONTAINS(?itemLabel, " ") || ?itemLabel = "{ingredient_name}")
              
              OPTIONAL {{ ?item schema:description ?description . }}
              FILTER(LANG(?description) = "en")
              
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }}
            ORDER BY STRLEN(?itemLabel)  # Shorter names first
            LIMIT 3
            """
            
            self.sparql.setQuery(contains_query)
            result = self.sparql.query().convert()
            
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                # Filter out obvious dishes/products in favor of basic ingredients
                for binding in bindings:
                    item_label = binding['itemLabel']['value'].lower()
                    
                    # Skip if it contains dish/product indicators
                    skip_keywords = ['dish', 'recipe', 'cuisine', 'food', 'cake', 'bread', 'soup', 'sauce']
                    description = binding.get('description', {}).get('value', '').lower()
                    
                    is_dish = any(keyword in description for keyword in skip_keywords)
                    
                    # Prefer exact word matches
                    is_exact_word = item_label == ingredient_name.lower()
                    
                    if is_exact_word or not is_dish:
                        item_uri = binding['item']['value']
                        logger.info(f"Found Wikidata entity (contains search) for '{ingredient_name}': {item_label} ({item_uri})")
                        return item_uri
                
                # If all options seem to be dishes, take the first one
                item_uri = bindings[0]['item']['value']
                item_label = bindings[0]['itemLabel']['value']
                logger.info(f"Found Wikidata entity (fallback) for '{ingredient_name}': {item_label} ({item_uri})")
                return item_uri
                
        except Exception as e:
            logger.error(f"Error searching Wikidata for '{ingredient_name}': {e}")
        
        logger.info(f"No Wikidata entity found for ingredient: {ingredient_name}")
        return None

    def get_nutritional_data(self, entity_uri: str) -> Dict:
        """
        Get nutritional information for a Wikidata entity
        """
        try:
            # Extract entity ID from URI
            entity_id = entity_uri.split('/')[-1]
            
            query = f"""
            SELECT DISTINCT ?property ?propertyLabel ?value ?unitLabel ?valueLabel WHERE {{
              wd:{entity_id} ?property ?value .
              
              # Nutritional properties
              VALUES ?property {{
                wdt:P2043    # length/size
                wdt:P2067    # mass  
                wdt:P2076    # energy value
                wdt:P2844    # carbohydrate content
                wdt:P2864    # protein content
                wdt:P2887    # fat content
                wdt:P3074    # fiber content
                wdt:P3078    # vitamin C content
                wdt:P3082    # calcium content
                wdt:P3083    # iron content
                wdt:P3087    # sodium content
                wdt:P3088    # potassium content
                wdt:P527     # has part/ingredient
              }}
              
              OPTIONAL {{ ?value wdt:P31 ?valueType . }}
              OPTIONAL {{ ?value wdt:P2044 ?unit . }}
              
              SERVICE wikibase:label {{ 
                bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
                ?property rdfs:label ?propertyLabel .
                ?value rdfs:label ?valueLabel .
                ?unit rdfs:label ?unitLabel .
              }}
            }}
            """
            
            self.sparql.setQuery(query)
            result = self.sparql.query().convert()
            
            nutritional_data = {}
            entity_label = entity_id  # Default fallback
            
            # Also get basic info about the entity
            info_query = f"""
            SELECT ?itemLabel ?description WHERE {{
              wd:{entity_id} rdfs:label ?itemLabel .
              OPTIONAL {{ wd:{entity_id} schema:description ?description . }}
              FILTER(LANG(?itemLabel) = "en")
              FILTER(LANG(?description) = "en")
            }}
            LIMIT 1
            """
            
            self.sparql.setQuery(info_query)
            info_result = self.sparql.query().convert()
            
            if info_result.get('results', {}).get('bindings'):
                info_binding = info_result['results']['bindings'][0]
                entity_label = info_binding.get('itemLabel', {}).get('value', entity_id)
                if 'description' in info_binding:
                    nutritional_data['description'] = info_binding['description']['value']
            
            # Process nutritional properties
            bindings = result.get('results', {}).get('bindings', [])
            
            # Map Wikidata properties to our fields
            property_mapping = {
                'P2076': 'calories_per_100g',    # energy value
                'P2844': 'carbohydrates_g',      # carbohydrate content  
                'P2864': 'protein_g',            # protein content
                'P2887': 'fat_g',                # fat content
                'P3074': 'fiber_g',              # fiber content
                'P3078': 'vitamin_c_mg',         # vitamin C content
                'P3082': 'calcium_mg',           # calcium content
                'P3083': 'iron_mg',              # iron content
                'P3087': 'sodium_mg',            # sodium content
                'P3088': 'potassium_mg'          # potassium content
            }
            
            for binding in bindings:
                property_uri = binding.get('property', {}).get('value', '')
                property_id = property_uri.split('/')[-1] if property_uri else ''
                value = binding.get('value', {}).get('value', '')
                
                if property_id in property_mapping and value:
                    field_name = property_mapping[property_id]
                    numeric_value = self._extract_numeric_value(value)
                    if numeric_value is not None:
                        nutritional_data[field_name] = numeric_value
            
            nutritional_data['wikidata_entity'] = entity_uri
            nutritional_data['entity_label'] = entity_label
            
            return nutritional_data
            
        except Exception as e:
            logger.error(f"Error getting nutritional data from {entity_uri}: {e}")
            return {}

    def _extract_numeric_value(self, value_str: str) -> Optional[float]:
        """Extract numeric value from Wikidata property value"""
        if not value_str:
            return None
            
        try:
            # Try to extract number directly
            if value_str.replace('.', '').replace('-', '').isdigit():
                return float(value_str)
            
            # Extract from strings with units
            import re
            numbers = re.findall(r'[\d.]+', str(value_str))
            if numbers:
                return float(numbers[0])
                
        except (ValueError, TypeError):
            pass
        
        return None

    def enrich_ingredient(self, ingredient_name: str) -> Dict:
        """
        Main method to enrich an ingredient with Wikidata data
        """
        try:
            # Search for ingredient in Wikidata
            entity_uri = self.search_ingredient_in_wikidata(ingredient_name)
            
            if not entity_uri:
                return {
                    'ingredient_name': ingredient_name,
                    'wikidata_found': False,
                    'error': 'No Wikidata entity found'
                }
            
            # Get nutritional data
            nutritional_data = self.get_nutritional_data(entity_uri)
            
            result = {
                'ingredient_name': ingredient_name,
                'wikidata_found': True,
                'wikidata_entity': entity_uri,
                **nutritional_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error enriching ingredient '{ingredient_name}': {e}")
            return {
                'ingredient_name': ingredient_name,
                'wikidata_found': False,
                'error': str(e)
            }


# Test function
def test_wikidata_enricher():
    enricher = WikidataEnricher()
    
    # Test dengan beberapa ingredient
    test_ingredients = ["tomato", "rice", "apple", "potato", "carrot"]
    
    for ingredient in test_ingredients:
        print(f"\n{'='*50}")
        print(f"Testing: {ingredient}")
        print('='*50)
        
        result = enricher.enrich_ingredient(ingredient)
        
        if result['wikidata_found']:
            print(f"✅ Found data for {ingredient}")
            print(f"Entity: {result.get('entity_label', 'N/A')}")
            print(f"URI: {result.get('wikidata_entity', 'N/A')}")
            
            # Print nutritional data
            nutritional_keys = ['calories_per_100g', 'carbohydrates_g', 'protein_g', 'fat_g', 'fiber_g']
            for key in nutritional_keys:
                if key in result and result[key]:
                    print(f"{key}: {result[key]}")
            
            if 'description' in result:
                print(f"Description: {result['description'][:150]}...")
        else:
            print(f"❌ No data found for {ingredient}")
            print(f"Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    test_wikidata_enricher()