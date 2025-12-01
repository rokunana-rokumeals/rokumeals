import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger(__name__)

class DBpediaEnricher:
    def __init__(self):
        self.endpoint_url = "http://dbpedia.org/sparql"

    def _query(self, query):
        """Execute SPARQL query using urllib"""
        params = {
            "default-graph-uri": "http://dbpedia.org",
            "query": query,
            "format": "application/json"
        }
        
        try:
            url = self.endpoint_url + "?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(url, timeout=5) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            logger.error(f"SPARQL query error: {e}")
            return None

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
        LIMIT 1
        """
        results = self._query(query)
        if results and results["results"]["bindings"]:
            return results["results"]["bindings"][0]["abstract"]["value"]
        return None

    def search_ingredient_in_dbpedia(self, ingredient_name):
        """Search for ingredient in DBpedia and return Info Box data"""
        try:
            # Clean ingredient name
            resource_name = ingredient_name.replace(" ", "_").replace(",", "").title()
            
            # Query for Info Box data
            query = f"""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dbr: <http://dbpedia.org/resource/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?abstract ?thumbnail ?wikiLink ?scientificName ?kingdom
            WHERE {{
                {{
                    dbr:{resource_name} dbo:abstract ?abstract .
                    FILTER (lang(?abstract) = 'en')
                    OPTIONAL {{ dbr:{resource_name} dbo:thumbnail ?thumbnail }}
                    OPTIONAL {{ dbr:{resource_name} foaf:isPrimaryTopicOf ?wikiLink }}
                    OPTIONAL {{ dbr:{resource_name} dbo:scientificName ?scientificName }}
                    OPTIONAL {{ dbr:{resource_name} dbo:kingdom ?kingdom }}
                }}
                UNION
                {{
                    ?res rdfs:label "{ingredient_name}"@en .
                    ?res a dbo:Food .
                    ?res dbo:abstract ?abstract .
                    FILTER (lang(?abstract) = 'en')
                    OPTIONAL {{ ?res dbo:thumbnail ?thumbnail }}
                    OPTIONAL {{ ?res foaf:isPrimaryTopicOf ?wikiLink }}
                    OPTIONAL {{ ?res dbo:scientificName ?scientificName }}
                }}
            }} LIMIT 1
            """
            
            results = self._query(query)
            
            if results and results["results"]["bindings"]:
                result = results["results"]["bindings"][0]
                return {
                    'source': 'DBpedia',
                    'abstract': result.get('abstract', {}).get('value'),
                    'thumbnail': result.get('thumbnail', {}).get('value'),
                    'wikiLink': result.get('wikiLink', {}).get('value'),
                    'scientificName': result.get('scientificName', {}).get('value'),
                    'kingdom': result.get('kingdom', {}).get('value'),
                }
            
            logger.info(f"No DBpedia data found for ingredient: {ingredient_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error searching DBpedia for '{ingredient_name}': {e}")
            return None