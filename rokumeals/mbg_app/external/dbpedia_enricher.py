"""
DBpedia SPARQL Integration for Ingredient Nutritional Enrichment
================================================================

This module queries DBpedia to enrich ingredient data with additional nutritional information.
DBpedia contains structured data about food items including vitamins, minerals, and nutritional facts.
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)

class DBpediaEnricher:
    """
    Enriches ingredient data using DBpedia SPARQL endpoint
    """
    
    DBPEDIA_ENDPOINT = "https://dbpedia.org/sparql"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MBG-Knowledge-Graph/1.0 (https://github.com/your-repo)',
            'Accept': 'application/json'
        })
    
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
    
    def search_ingredient_in_dbpedia(self, ingredient_name: str) -> List[Dict]:
        """
        Search for ingredient in DBpedia using SPARQL
        Returns list of potential matches with their URIs
        """
        clean_name = self.clean_ingredient_name(ingredient_name)
        
        # More robust SPARQL query with proper escaping
        sparql_query = """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT DISTINCT ?food ?label WHERE {
            ?food rdf:type dbo:Food .
            ?food rdfs:label ?label .
            
            FILTER (
                CONTAINS(LCASE(?label), "%s")
            )
            FILTER (LANG(?label) = "en")
        }
        LIMIT 5
        """ % clean_name.lower()
        
        try:
            response = self.session.post(
                self.DBPEDIA_ENDPOINT,
                data={
                    'query': sparql_query,
                    'format': 'json'
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/sparql-results+json'
                },
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for binding in data.get('results', {}).get('bindings', []):
                results.append({
                    'uri': binding['food']['value'],
                    'label': binding['label']['value'],
                    'abstract': ''  # We'll get this separately if needed
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching DBpedia for '{ingredient_name}': {str(e)}")
            # Fallback to direct resource lookup
            return self._fallback_search(ingredient_name)
    
    def _fallback_search(self, ingredient_name: str) -> List[Dict]:
        """
        Fallback method using direct DBpedia resource lookup
        """
        clean_name = self.clean_ingredient_name(ingredient_name).title()
        
        # Common ingredient variations for DBpedia
        variations = [
            clean_name,
            clean_name.capitalize(),
            clean_name.lower(),
            f"{clean_name}_(food)" if not clean_name.endswith("_food") else clean_name
        ]
        
        results = []
        for variant in variations:
            try:
                # Try direct resource access
                resource_url = f"http://dbpedia.org/resource/{variant.replace(' ', '_')}"
                
                # Check if resource exists using simple HTTP HEAD
                response = self.session.head(resource_url, timeout=5)
                if response.status_code == 200:
                    results.append({
                        'uri': resource_url,
                        'label': variant,
                        'abstract': f"DBpedia resource for {variant}"
                    })
                    break
                    
            except Exception:
                continue
        
        return results
    
    def get_nutritional_data(self, dbpedia_uri: str) -> Dict:
        """
        Get detailed nutritional information for a specific DBpedia food item
        """
        
        # Extract resource name from URI
        resource_name = dbpedia_uri.replace('http://dbpedia.org/resource/', '')
        
        # More conservative SPARQL query for nutritional data
        sparql_query = """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbp: <http://dbpedia.org/property/>
        
        SELECT ?property ?value WHERE {
            <%s> ?property ?value .
            
            FILTER (
                ?property = dbo:carbohydrate ||
                ?property = dbo:fat ||
                ?property = dbo:protein ||
                ?property = dbo:energy
            )
        }
        """ % dbpedia_uri
        
        try:
            response = self.session.post(
                self.DBPEDIA_ENDPOINT,
                data={
                    'query': sparql_query,
                    'format': 'json'
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/sparql-results+json'
                },
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            nutrition_data = {}
            
            for binding in data.get('results', {}).get('bindings', []):
                property_uri = binding['property']['value']
                value = binding['value']['value']
                
                # Map DBpedia properties to our fields
                property_mapping = {
                    'http://dbpedia.org/ontology/carbohydrate': 'carbohydrates_g',
                    'http://dbpedia.org/ontology/fat': 'fat_g',
                    'http://dbpedia.org/ontology/protein': 'protein_g', 
                    'http://dbpedia.org/ontology/energy': 'energy_kcal',
                    'http://dbpedia.org/property/vitaminC': 'vitamin_c_mg',
                    'http://dbpedia.org/property/calcium': 'calcium_mg',
                    'http://dbpedia.org/property/iron': 'iron_mg',
                    'http://dbpedia.org/property/fiber': 'fiber_g',
                    'http://dbpedia.org/property/sugar': 'sugar_g',
                    'http://dbpedia.org/property/sodium': 'sodium_mg',
                    'http://dbpedia.org/property/potassium': 'potassium_mg',
                    'http://dbpedia.org/property/vitaminA': 'vitamin_a_ug',
                    'http://dbpedia.org/property/vitaminB6': 'vitamin_b6_mg',
                    'http://dbpedia.org/property/magnesium': 'magnesium_mg',
                    'http://dbpedia.org/property/zinc': 'zinc_mg'
                }
                
                field_name = property_mapping.get(property_uri)
                if field_name:
                    # Extract numeric value
                    numeric_value = self._extract_numeric_value(value)
                    if numeric_value is not None:
                        nutrition_data[field_name] = numeric_value
            
            return nutrition_data
            
        except Exception as e:
            logger.error(f"Error getting nutritional data for {dbpedia_uri}: {str(e)}")
            return {}
    
    def _extract_numeric_value(self, value_str: str) -> Optional[float]:
        """
        Extract numeric value from DBpedia property value
        Handles various formats like "12.5 g", "15mg", "150 kcal", etc.
        """
        try:
            # Remove common units and extract number
            clean_value = re.sub(r'[a-zA-Z\s%]+', '', str(value_str))
            
            # Handle decimal values
            match = re.search(r'(\d+\.?\d*)', clean_value)
            if match:
                return float(match.group(1))
            
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def enrich_ingredient(self, ingredient_name: str) -> Dict:
        """
        Main method to enrich an ingredient with DBpedia data
        Returns enriched nutritional data or empty dict if not found
        """
        logger.info(f"Enriching ingredient: {ingredient_name}")
        
        # Step 1: Search for ingredient in DBpedia
        search_results = self.search_ingredient_in_dbpedia(ingredient_name)
        
        if not search_results:
            logger.info(f"No DBpedia results found for: {ingredient_name}")
            return {}
        
        # Step 2: Get nutritional data from best match
        best_match = search_results[0]  # Take first result as best match
        logger.info(f"Found match: {best_match['label']} ({best_match['uri']})")
        
        nutritional_data = self.get_nutritional_data(best_match['uri'])
        
        if nutritional_data:
            # Add metadata
            nutritional_data['dbpedia_uri'] = best_match['uri']
            nutritional_data['dbpedia_label'] = best_match['label']
            nutritional_data['enriched_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Successfully enriched {ingredient_name} with {len(nutritional_data)} properties")
        else:
            logger.info(f"No nutritional data found for {ingredient_name}")
        
        return nutritional_data
    
    def enrich_ingredients_batch(self, ingredient_names: List[str], batch_delay: float = 1.0) -> Dict[str, Dict]:
        """
        Enrich multiple ingredients with rate limiting
        Returns dict mapping ingredient names to their enriched data
        """
        results = {}
        
        for i, ingredient_name in enumerate(ingredient_names):
            logger.info(f"Processing {i+1}/{len(ingredient_names)}: {ingredient_name}")
            
            try:
                enriched_data = self.enrich_ingredient(ingredient_name)
                results[ingredient_name] = enriched_data
                
                # Rate limiting
                if batch_delay > 0:
                    time.sleep(batch_delay)
                    
            except Exception as e:
                logger.error(f"Failed to process {ingredient_name}: {str(e)}")
                results[ingredient_name] = {}
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Test the enricher
    enricher = DBpediaEnricher()
    
    # Test with some common ingredients
    test_ingredients = [
        "tomato",
        "chicken breast", 
        "spinach",
        "olive oil",
        "garlic"
    ]
    
    print("=== Testing DBpedia Enrichment ===")
    for ingredient in test_ingredients:
        print(f"\nTesting: {ingredient}")
        result = enricher.enrich_ingredient(ingredient)
        
        if result:
            print("✅ Found enrichment data:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print("❌ No enrichment data found")