# External Data Integration Queries
# Collection of SPARQL queries to enrich the MBG Knowledge Graph with external data

## DBpedia Ingredient Enrichment Queries

### 1. Get Basic Information for Food Ingredients
```sparql
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?ingredient ?label ?abstract ?type ?thumbnail WHERE {
    VALUES ?ingredientName { 
        "Chicken" "Beef" "Pork" "Salmon" "Tuna" "Shrimp" 
        "Tomato" "Onion" "Garlic" "Potato" "Carrot" "Broccoli"
        "Rice" "Wheat" "Corn" "Quinoa" "Oats" "Barley"
        "Milk" "Cheese" "Butter" "Yogurt" "Eggs"
        "Olive_oil" "Coconut_oil" "Honey" "Sugar" "Salt" "Pepper"
    }
    
    ?ingredient rdfs:label ?ingredientName@en .
    ?ingredient rdfs:label ?label .
    FILTER(LANG(?label) = "en")
    
    OPTIONAL { ?ingredient dbo:abstract ?abstract . FILTER(LANG(?abstract) = "en") }
    OPTIONAL { ?ingredient a ?type . FILTER(?type = dbo:Food || ?type = dbo:Ingredient) }
    OPTIONAL { ?ingredient dbo:thumbnail ?thumbnail }
    
    FILTER(CONTAINS(LCASE(?label), LCASE(?ingredientName)))
}
LIMIT 100
```

### 2. Get Nutritional Information
```sparql
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?ingredient ?label ?calories ?protein ?fat ?carbohydrate WHERE {
    VALUES ?ingredientName { 
        "Chicken_breast" "Beef_steak" "Salmon" "Brown_rice" "Quinoa"
        "Broccoli" "Spinach" "Sweet_potato" "Avocado" "Almonds"
    }
    
    ?ingredient rdfs:label ?ingredientName@en .
    ?ingredient rdfs:label ?label .
    FILTER(LANG(?label) = "en")
    
    OPTIONAL { ?ingredient dbp:calories ?calories }
    OPTIONAL { ?ingredient dbp:protein ?protein }
    OPTIONAL { ?ingredient dbp:fat ?fat }
    OPTIONAL { ?ingredient dbp:carbohydrate ?carbohydrate }
    OPTIONAL { ?ingredient dbo:calories ?calories2 }
    
    FILTER(CONTAINS(LCASE(?label), LCASE(?ingredientName)))
}
LIMIT 50
```

### 3. Get Food Categories and Classifications
```sparql
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dct: <http://purl.org/dc/terms/>

SELECT DISTINCT ?ingredient ?label ?category ?broader ?subject WHERE {
    VALUES ?ingredientName { 
        "Chicken" "Beef" "Salmon" "Rice" "Wheat" "Tomato" "Onion"
        "Milk" "Cheese" "Olive_oil" "Honey" "Sugar"
    }
    
    ?ingredient rdfs:label ?ingredientName@en .
    ?ingredient rdfs:label ?label .
    FILTER(LANG(?label) = "en")
    
    OPTIONAL { 
        ?ingredient dct:subject ?subject .
        FILTER(CONTAINS(STR(?subject), "food") || CONTAINS(STR(?subject), "cuisine") || CONTAINS(STR(?subject), "ingredient"))
    }
    
    OPTIONAL { ?ingredient dbo:type ?category }
    OPTIONAL { ?ingredient dbo:genus ?broader }
    
    FILTER(CONTAINS(LCASE(?label), LCASE(?ingredientName)))
}
LIMIT 100
```

## Wikidata Enrichment Queries

### 4. Get Comprehensive Food Data from Wikidata
```sparql
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?item ?itemLabel ?description ?calories ?protein ?fat ?carbs ?category ?image WHERE {
    VALUES ?foodType { wd:Q2095 wd:Q42527 wd:Q20191 wd:Q746549 }  # food, meat, vegetable, ingredient
    
    ?item wdt:P31 ?foodType .
    ?item rdfs:label ?itemLabel .
    FILTER(LANG(?itemLabel) = "en")
    
    OPTIONAL { ?item schema:description ?description . FILTER(LANG(?description) = "en") }
    OPTIONAL { ?item wdt:P2928 ?calories }  # energy value
    OPTIONAL { ?item wdt:P2629 ?protein }  # protein content
    OPTIONAL { ?item wdt:P2630 ?fat }      # fat content  
    OPTIONAL { ?item wdt:P2632 ?carbs }    # carbohydrate content
    OPTIONAL { ?item wdt:P279 ?category }  # subclass of
    OPTIONAL { ?item wdt:P18 ?image }      # image
    
    FILTER(REGEX(?itemLabel, "(chicken|beef|salmon|rice|tomato|onion|milk|cheese)", "i"))
}
LIMIT 50
```

### 5. Get Cooking Methods and Cuisines
```sparql
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?method ?methodLabel ?description ?cuisine ?cuisineLabel WHERE {
    {
        ?method wdt:P31 wd:Q2297928 .  # cooking technique
        ?method rdfs:label ?methodLabel .
        FILTER(LANG(?methodLabel) = "en")
        OPTIONAL { ?method schema:description ?description . FILTER(LANG(?description) = "en") }
    }
    UNION
    {
        ?cuisine wdt:P31 wd:Q1968435 .  # cuisine
        ?cuisine rdfs:label ?cuisineLabel .
        FILTER(LANG(?cuisineLabel) = "en")
        OPTIONAL { ?cuisine schema:description ?description . FILTER(LANG(?description) = "en") }
    }
}
LIMIT 100
```

## Recipe and Dish Enhancement

### 6. Get Popular Dishes from DBpedia
```sparql
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?dish ?label ?abstract ?cuisine ?origin ?ingredients WHERE {
    ?dish a dbo:Food .
    ?dish rdfs:label ?label .
    FILTER(LANG(?label) = "en")
    
    OPTIONAL { ?dish dbo:abstract ?abstract . FILTER(LANG(?abstract) = "en") }
    OPTIONAL { ?dish dbo:cuisine ?cuisine }
    OPTIONAL { ?dish dbo:country ?origin }
    OPTIONAL { ?dish dbp:mainIngredient ?ingredients }
    
    FILTER(REGEX(?label, "(pasta|pizza|soup|salad|curry|stir|grilled|roasted)", "i"))
}
LIMIT 50
```

### 7. Get Health and Dietary Information
```sparql
PREFIX dbr: <http://dbpedia.org/resource/>
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX dbp: <http://dbpedia.org/property/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?food ?label ?calories ?protein ?fat ?vitaminC ?vitaminA ?iron WHERE {
    ?food a dbo:Food .
    ?food rdfs:label ?label .
    FILTER(LANG(?label) = "en")
    
    OPTIONAL { ?food dbp:calories ?calories }
    OPTIONAL { ?food dbp:protein ?protein }
    OPTIONAL { ?food dbp:fat ?fat }
    OPTIONAL { ?food dbp:vitaminC ?vitaminC }
    OPTIONAL { ?food dbp:vitaminA ?vitaminA }
    OPTIONAL { ?food dbp:iron ?iron }
    
    FILTER(BOUND(?calories) || BOUND(?protein) || BOUND(?fat) || BOUND(?vitaminC))
}
LIMIT 100
```

## Usage Instructions

### For DBpedia (SPARQL Endpoint: http://dbpedia.org/sparql):
1. Copy any of the DBpedia queries
2. Go to http://dbpedia.org/sparql  
3. Paste the query and execute
4. Export results as JSON/CSV for integration

### For Wikidata (SPARQL Endpoint: https://query.wikidata.org/):
1. Copy any of the Wikidata queries
2. Go to https://query.wikidata.org/
3. Paste the query and execute  
4. Download results in preferred format

### Integration Strategy:
1. **Match by Name**: Link external data to existing ingredients by name matching
2. **Enrich Descriptions**: Add abstracts and detailed descriptions from external sources
3. **Add Images**: Include thumbnails/images for better UI
4. **Nutritional Enhancement**: Supplement missing nutritional data
5. **Category Mapping**: Map external categories to internal classification system
6. **Create New Relationships**: Add relationships like "originatesFrom", "usedInCuisine", etc.

### Sample Integration Code:
```python
# Example: Integrate DBpedia data with Neo4j
def integrate_external_data(neo4j_session, external_data):
    for item in external_data:
        query = """
        MATCH (i:Ingredient {name: $ingredient_name})
        SET i.external_description = $description,
            i.external_image = $thumbnail,
            i.dbpedia_uri = $uri
        """
        neo4j_session.run(query, 
                         ingredient_name=item['label'],
                         description=item.get('abstract', ''),
                         thumbnail=item.get('thumbnail', ''),
                         uri=item['ingredient'])
```

This collection provides comprehensive external data enrichment for the MBG Knowledge Graph!