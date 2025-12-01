from SPARQLWrapper import SPARQLWrapper, JSON
import logging

logger = logging.getLogger(__name__)

class DBpediaEnricher:
    def __init__(self):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)
    
    def get_dbpedia_data(self, resource_name):
        """Get basic abstract data from DBpedia"""
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT ?abstract
        WHERE {{
          dbr:{resource_name} dbo:abstract ?abstract .
          FILTER (lang(?abstract) = 'en')
        }}
        """
        self.sparql.setQuery(query)
        try:
            results = self.sparql.query().convert()
            if results["results"]["bindings"]:
                return results["results"]["bindings"][0]["abstract"]["value"]
        except Exception as e:
            logger.error(f"Error querying DBpedia for {resource_name}: {e}")
        return None

    def search_ingredient_in_dbpedia(self, ingredient_name):
        """Search for ingredient in DBpedia and return basic info"""
        try:
            # Clean ingredient name for DBpedia resource format
            resource_name = ingredient_name.replace(" ", "_").replace(",", "")
            
            # Try to get abstract first
            abstract = self.get_dbpedia_data(resource_name)
            if abstract:
                return {
                    'resource': f"http://dbpedia.org/resource/{resource_name}",
                    'abstract': abstract
                }
            
            # If no direct match, try alternative formats
            alternatives = [
                ingredient_name.title().replace(" ", "_"),
                ingredient_name.lower().replace(" ", "_"),
                ingredient_name.capitalize().replace(" ", "_")
            ]
            
            for alt_name in alternatives:
                abstract = self.get_dbpedia_data(alt_name)
                if abstract:
                    return {
                        'resource': f"http://dbpedia.org/resource/{alt_name}",
                        'abstract': abstract
                    }
            
            logger.info(f"No DBpedia data found for ingredient: {ingredient_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching DBpedia for '{ingredient_name}': {e}")
            return None

    def get_nutritional_data(self, ingredient_name):
        """Get nutritional information for an ingredient"""
        try:
            # Clean ingredient name for DBpedia resource format
            resource_name = ingredient_name.replace(" ", "_").replace(",", "")
            
            query = f"""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dbr: <http://dbpedia.org/resource/>
            PREFIX dbp: <http://dbpedia.org/property/>

            SELECT ?calories ?carbs ?protein ?fat ?fiber ?vitamin_c ?calcium ?iron
            WHERE {{
              OPTIONAL {{ dbr:{resource_name} dbo:energyPer100g ?calories . }}
              OPTIONAL {{ dbr:{resource_name} dbo:carbohydratePer100g ?carbs . }}
              OPTIONAL {{ dbr:{resource_name} dbo:proteinPer100g ?protein . }}
              OPTIONAL {{ dbr:{resource_name} dbo:fatPer100g ?fat . }}
              OPTIONAL {{ dbr:{resource_name} dbp:fiber ?fiber . }}
              OPTIONAL {{ dbr:{resource_name} dbp:vitc ?vitamin_c . }}
              OPTIONAL {{ dbr:{resource_name} dbp:calcium ?calcium . }}
              OPTIONAL {{ dbr:{resource_name} dbp:iron ?iron . }}
            }}
            """
            
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            
            nutritional_info = {}
            if results["results"]["bindings"]:
                binding = results["results"]["bindings"][0]
                
                # Extract nutritional values if they exist
                for key in ['calories', 'carbs', 'protein', 'fat', 'fiber', 'vitamin_c', 'calcium', 'iron']:
                    if key in binding and binding[key]:
                        value = binding[key]['value']
                        try:
                            # Try to convert to float for numerical values
                            nutritional_info[key] = float(value)
                        except ValueError:
                            # Keep as string if not numerical
                            nutritional_info[key] = value
            
            return nutritional_info if nutritional_info else None
            
        except Exception as e:
            logger.error(f"Error getting nutritional data for '{ingredient_name}': {e}")
            return None

def explore_dbpedia():
    """Explore what data is actually available in DBpedia"""
    enricher = DBpediaEnricher()
    
    # First, let's check if we can connect and what types of data exist
    print("1. Testing basic DBpedia connection...")
    
    basic_query = """
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?resource ?label
    WHERE {
        ?resource rdfs:label ?label .
        FILTER (lang(?label) = 'en')
        FILTER (CONTAINS(LCASE(?label), "tomato"))
    }
    LIMIT 10
    """
    
    enricher.sparql.setQuery(basic_query)
    try:
        results = enricher.sparql.query().convert()
        if results["results"]["bindings"]:
            print("Found these tomato-related resources:")
            for binding in results["results"]["bindings"]:
                resource = binding["resource"]["value"]
                label = binding["label"]["value"]
                print(f"  {label}: {resource}")
        else:
            print("No tomato resources found")
    except Exception as e:
        print(f"Connection error: {e}")
        return
    
    print("\n2. Let's check what properties are available for Tomato...")
    
    # Check what properties exist for tomato
    properties_query = """
    PREFIX dbr: <http://dbpedia.org/resource/>
    
    SELECT ?property ?value
    WHERE {
        dbr:Tomato ?property ?value .
    }
    LIMIT 20
    """
    
    enricher.sparql.setQuery(properties_query)
    try:
        results = enricher.sparql.query().convert()
        if results["results"]["bindings"]:
            print("Properties available for dbr:Tomato:")
            for binding in results["results"]["bindings"]:
                prop = binding["property"]["value"]
                value = str(binding["value"]["value"])
                print(f"  {prop}: {value[:100]}...")
        else:
            print("No properties found for dbr:Tomato")
    except Exception as e:
        print(f"Error getting properties: {e}")
    
    print("\n3. Let's check nutritional ontology classes...")
    
    # Check if there are nutritional classes
    nutrition_query = """
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?class ?label
    WHERE {
        ?class rdfs:label ?label .
        FILTER (lang(?label) = 'en')
        FILTER (
            CONTAINS(LCASE(?label), "nutrition") ||
            CONTAINS(LCASE(?label), "vitamin") ||
            CONTAINS(LCASE(?label), "mineral") ||
            CONTAINS(LCASE(?label), "calorie")
        )
    }
    LIMIT 10
    """
    
    enricher.sparql.setQuery(nutrition_query)
    try:
        results = enricher.sparql.query().convert()
        if results["results"]["bindings"]:
            print("Nutrition-related classes:")
            for binding in results["results"]["bindings"]:
                cls = binding["class"]["value"]
                label = binding["label"]["value"]
                print(f"  {label}: {cls}")
        else:
            print("No nutrition classes found")
    except Exception as e:
        print(f"Error getting nutrition classes: {e}")

# Test function
def test_dbpedia():
    explore_dbpedia()

if __name__ == "__main__":
    test_dbpedia()