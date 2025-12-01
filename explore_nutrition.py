import requests
import json

def explore_tomato_nutrition():
    """Explore all nutrition-related properties for Tomato"""
    
    endpoint = "https://dbpedia.org/sparql"
    
    # Get all properties for tomato
    query = """
    PREFIX dbp: <http://dbpedia.org/property/>
    
    SELECT ?p ?o 
    WHERE {
        <http://dbpedia.org/resource/Tomato> ?p ?o .
    }
    """
    
    params = {
        'query': query,
        'format': 'json'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/sparql-results+json'
    }
    
    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            
            print(f"All properties for Tomato ({len(bindings)} total):")
            
            nutrition_props = []
            other_props = []
            
            for binding in bindings:
                prop = binding['p']['value']
                value = str(binding['o']['value'])
                
                # Check if it's nutrition related
                if any(term in prop.lower() for term in ['carb', 'protein', 'fat', 'calorie', 'energy', 'vitamin', 'mineral', 'fiber', 'sodium', 'sugar']):
                    nutrition_props.append((prop, value))
                else:
                    other_props.append((prop, value))
            
            print(f"\n🍅 NUTRITIONAL PROPERTIES ({len(nutrition_props)}):")
            for prop, value in nutrition_props:
                print(f"  {prop}: {value}")
            
            print(f"\n📋 OTHER INTERESTING PROPERTIES (showing first 10 of {len(other_props)}):")
            for prop, value in other_props[:10]:
                if 'abstract' in prop.lower() or 'label' in prop.lower() or 'comment' in prop.lower():
                    print(f"  ⭐ {prop}: {value[:150]}...")
                else:
                    print(f"  {prop}: {value[:100]}...")
                    
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

def test_other_foods():
    """Test nutrition data for other common ingredients"""
    
    foods = ["Rice", "Potato", "Chicken", "Beef", "Milk", "Bread"]
    
    endpoint = "https://dbpedia.org/sparql"
    
    for food in foods:
        print(f"\n{'='*40}")
        print(f"Testing {food}...")
        
        query = f"""
        PREFIX dbp: <http://dbpedia.org/property/>
        
        SELECT ?p ?o 
        WHERE {{
            <http://dbpedia.org/resource/{food}> ?p ?o .
            FILTER(
                CONTAINS(LCASE(STR(?p)), "carb") ||
                CONTAINS(LCASE(STR(?p)), "protein") ||
                CONTAINS(LCASE(STR(?p)), "fat") ||
                CONTAINS(LCASE(STR(?p)), "calorie") ||
                CONTAINS(LCASE(STR(?p)), "energy")
            )
        }}
        """
        
        params = {
            'query': query,
            'format': 'json'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/sparql-results+json'
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                bindings = data.get('results', {}).get('bindings', [])
                
                if bindings:
                    print(f"  Found {len(bindings)} nutritional properties:")
                    for binding in bindings:
                        prop = binding['p']['value']
                        value = binding['o']['value']
                        print(f"    {prop.split('/')[-1]}: {value}")
                else:
                    print(f"  No nutritional data found for {food}")
            else:
                print(f"  Error {response.status_code} for {food}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    explore_tomato_nutrition()
    test_other_foods()