import requests
import json

def test_dbpedia_simple():
    """Test DBpedia endpoint dengan request biasa"""
    
    # Test endpoint availability
    print("Testing DBpedia endpoint...")
    
    endpoint = "https://dbpedia.org/sparql"
    
    # Simple SPARQL query
    query = """
    SELECT ?s ?p ?o 
    WHERE {
        <http://dbpedia.org/resource/Tomato> ?p ?o .
    }
    LIMIT 10
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
        print("Making request to DBpedia...")
        response = requests.get(endpoint, params=params, headers=headers, timeout=30)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            bindings = data.get('results', {}).get('bindings', [])
            
            print(f"Found {len(bindings)} properties for Tomato:")
            for binding in bindings:  # Show all properties
                prop = binding['p']['value']
                value = str(binding['o']['value'])
                
                # Filter for nutrition-related or interesting properties
                if any(term in prop.lower() for term in ['nutrition', 'calorie', 'energy', 'vitamin', 'mineral', 'carb', 'protein', 'fat', 'abstract', 'label']):
                    print(f"  ⭐ {prop}: {value[:150]}...")
                else:
                    print(f"  {prop}: {value[:100]}...")
        else:
            print(f"Error: {response.status_code} - {response.text[:200]}")
            
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Other error: {e}")

def test_nutritional_properties():
    """Test specifically for nutritional properties"""
    print("\n" + "="*60)
    print("Testing for nutritional properties...")
    
    endpoint = "https://dbpedia.org/sparql"
    
    # Look for nutritional data patterns
    query = """
    SELECT ?p ?o 
    WHERE {
        <http://dbpedia.org/resource/Tomato> ?p ?o .
        FILTER(
            CONTAINS(LCASE(STR(?p)), "nutrition") ||
            CONTAINS(LCASE(STR(?p)), "calorie") ||
            CONTAINS(LCASE(STR(?p)), "energy") ||
            CONTAINS(LCASE(STR(?p)), "vitamin") ||
            CONTAINS(LCASE(STR(?p)), "carb") ||
            CONTAINS(LCASE(STR(?p)), "protein") ||
            CONTAINS(LCASE(STR(?p)), "fat")
        )
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
            
            if bindings:
                print(f"Found {len(bindings)} nutritional properties:")
                for binding in bindings:
                    prop = binding['p']['value']
                    value = binding['o']['value']
                    print(f"  {prop}: {value}")
            else:
                print("No nutritional properties found using this approach")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

def test_abstract_and_basic_info():
    """Get basic info like abstract"""
    print("\n" + "="*60)
    print("Testing for abstract and basic info...")
    
    endpoint = "https://dbpedia.org/sparql"
    
    query = """
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?abstract ?label
    WHERE {
        <http://dbpedia.org/resource/Tomato> dbo:abstract ?abstract .
        <http://dbpedia.org/resource/Tomato> rdfs:label ?label .
        FILTER (lang(?abstract) = 'en')
        FILTER (lang(?label) = 'en')
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
            
            if bindings:
                binding = bindings[0]
                label = binding.get('label', {}).get('value', 'No label')
                abstract = binding.get('abstract', {}).get('value', 'No abstract')
                
                print(f"Label: {label}")
                print(f"Abstract: {abstract[:300]}...")
            else:
                print("No abstract found")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_dbpedia_simple()
    test_nutritional_properties()
    test_abstract_and_basic_info()