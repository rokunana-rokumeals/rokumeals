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
        Get comprehensive information for a Wikidata entity
        Including image, class, description, source, and nutritional facts
        """
        try:
            # Extract entity ID from URI
            entity_id = entity_uri.split('/')[-1]
            
            # Comprehensive query for general information
            query = f"""
            SELECT DISTINCT ?itemLabel ?description ?image ?instanceOfLabel ?subclassOfLabel 
                   ?madeFromLabel ?hasUseLabel ?hasCharacteristicLabel ?hasPartLabel
                   ?calories ?carbs ?protein ?fat ?fiber ?water ?sugar
                   ?vitaminC ?calcium ?iron ?sodium ?potassium ?magnesium
            WHERE {{
              wd:{entity_id} rdfs:label ?itemLabel .
              FILTER(LANG(?itemLabel) = "en")
              
              # Basic information
              OPTIONAL {{ wd:{entity_id} schema:description ?description . FILTER(LANG(?description) = "en") }}
              OPTIONAL {{ wd:{entity_id} wdt:P18 ?image . }}
              
              # Classification
              OPTIONAL {{ 
                wd:{entity_id} wdt:P31 ?instanceOf .
                ?instanceOf rdfs:label ?instanceOfLabel .
                FILTER(LANG(?instanceOfLabel) = "en")
              }}
              OPTIONAL {{ 
                wd:{entity_id} wdt:P279 ?subclassOf .
                ?subclassOf rdfs:label ?subclassOfLabel .
                FILTER(LANG(?subclassOfLabel) = "en")
              }}
              
              # Material and usage
              OPTIONAL {{ 
                wd:{entity_id} wdt:P186 ?madeFrom .
                ?madeFrom rdfs:label ?madeFromLabel .
                FILTER(LANG(?madeFromLabel) = "en")
              }}
              OPTIONAL {{ 
                wd:{entity_id} wdt:P366 ?hasUse .
                ?hasUse rdfs:label ?hasUseLabel .
                FILTER(LANG(?hasUseLabel) = "en")
              }}
              OPTIONAL {{ 
                wd:{entity_id} wdt:P1552 ?hasCharacteristic .
                ?hasCharacteristic rdfs:label ?hasCharacteristicLabel .
                FILTER(LANG(?hasCharacteristicLabel) = "en")
              }}
              OPTIONAL {{ 
                wd:{entity_id} wdt:P527 ?hasPart .
                ?hasPart rdfs:label ?hasPartLabel .
                FILTER(LANG(?hasPartLabel) = "en")
              }}
              
              # Nutritional information (various properties)
              OPTIONAL {{ wd:{entity_id} wdt:P2076 ?calories . }}        # energy value
              OPTIONAL {{ wd:{entity_id} wdt:P2844 ?carbs . }}           # carbohydrate content
              OPTIONAL {{ wd:{entity_id} wdt:P2864 ?protein . }}         # protein content  
              OPTIONAL {{ wd:{entity_id} wdt:P2887 ?fat . }}             # fat content
              OPTIONAL {{ wd:{entity_id} wdt:P3074 ?fiber . }}           # dietary fiber content
              OPTIONAL {{ wd:{entity_id} wdt:P527/wdt:P2067 ?water . }}  # water content
              OPTIONAL {{ wd:{entity_id} wdt:P5138 ?sugar . }}           # sugar content
              
              # Vitamins and minerals
              OPTIONAL {{ wd:{entity_id} wdt:P3078 ?vitaminC . }}        # vitamin C content
              OPTIONAL {{ wd:{entity_id} wdt:P3082 ?calcium . }}         # calcium content
              OPTIONAL {{ wd:{entity_id} wdt:P3083 ?iron . }}            # iron content
              OPTIONAL {{ wd:{entity_id} wdt:P3087 ?sodium . }}          # sodium content
              OPTIONAL {{ wd:{entity_id} wdt:P3088 ?potassium . }}       # potassium content
              OPTIONAL {{ wd:{entity_id} wdt:P3089 ?magnesium . }}       # magnesium content
              
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }}
            LIMIT 1
            """
            
            self.sparql.setQuery(query)
            result = self.sparql.query().convert()
            
            enriched_data = {}
            
            bindings = result.get('results', {}).get('bindings', [])
            if bindings:
                binding = bindings[0]
                
                # Basic information
                if 'itemLabel' in binding:
                    enriched_data['entity_label'] = binding['itemLabel']['value']
                
                if 'description' in binding:
                    enriched_data['description'] = binding['description']['value']
                
                if 'image' in binding:
                    enriched_data['image_url'] = binding['image']['value']
                
                # Classification information
                classifications = []
                if 'instanceOfLabel' in binding:
                    classifications.append(f"Instance of: {binding['instanceOfLabel']['value']}")
                if 'subclassOfLabel' in binding:
                    classifications.append(f"Subclass of: {binding['subclassOfLabel']['value']}")
                if classifications:
                    enriched_data['classification'] = "; ".join(classifications)
                
                # Material and usage information
                material_info = []
                if 'madeFromLabel' in binding:
                    material_info.append(f"Made from: {binding['madeFromLabel']['value']}")
                if 'hasUseLabel' in binding:
                    material_info.append(f"Used as: {binding['hasUseLabel']['value']}")
                if 'hasCharacteristicLabel' in binding:
                    material_info.append(f"Characteristic: {binding['hasCharacteristicLabel']['value']}")
                if 'hasPartLabel' in binding:
                    material_info.append(f"Contains: {binding['hasPartLabel']['value']}")
                if material_info:
                    enriched_data['material_info'] = "; ".join(material_info)
                
                # Nutritional data with proper extraction
                nutritional_fields = {
                    'calories': 'calories_per_100g',
                    'carbs': 'carbohydrates_g',
                    'protein': 'protein_g',
                    'fat': 'fat_g',
                    'fiber': 'fiber_g',
                    'water': 'water_g',
                    'sugar': 'sugar_g',
                    'vitaminC': 'vitamin_c_mg',
                    'calcium': 'calcium_mg',
                    'iron': 'iron_mg',
                    'sodium': 'sodium_mg',
                    'potassium': 'potassium_mg',
                    'magnesium': 'magnesium_mg'
                }
                
                for wikidata_field, our_field in nutritional_fields.items():
                    if wikidata_field in binding and binding[wikidata_field]:
                        value = binding[wikidata_field]['value']
                        numeric_value = self._extract_numeric_value(value)
                        if numeric_value is not None:
                            enriched_data[our_field] = numeric_value
            
            enriched_data['wikidata_entity'] = entity_uri
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Error getting comprehensive data from {entity_uri}: {e}")
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