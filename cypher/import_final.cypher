// ===========================================================================
// Meal Balance Grub (MBG) Knowledge Graph - Neo4j Import Script
// ===========================================================================
// This script imports the preprocessed CSV data into Neo4j as a Property Graph
// Run this script in Neo4j Browser or Neo4j Desktop

// Clear existing data (CAUTION: This removes all data!)
// MATCH (n) DETACH DELETE n;

// Create constraints for unique identifiers
CREATE CONSTRAINT recipe_id_unique IF NOT EXISTS FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE;
CREATE CONSTRAINT ingredient_id_unique IF NOT EXISTS FOR (i:Ingredient) REQUIRE i.ingredient_id IS UNIQUE;
CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (c:Category) REQUIRE c.category_id IS UNIQUE;

// ===========================================================================
// 1. IMPORT RECIPE NODES
// ===========================================================================
LOAD CSV WITH HEADERS FROM "file:///final_recipes.csv" AS row
CREATE (:Recipe {
    recipe_id: row.recipe_id,
    title: row.title,
    rating: toFloat(row.rating),
    calories: toFloat(row.calories),
    protein: toFloat(row.protein),
    fat: toFloat(row.fat),
    sodium: toFloat(row.sodium),
    description: row.description,
    directions: row.directions,
    ingredients_raw: row.ingredients_raw
});

// ===========================================================================
// 2. IMPORT INGREDIENT NODES
// ===========================================================================
LOAD CSV WITH HEADERS FROM "file:///final_ingredients.csv" AS row
CREATE (:Ingredient {
    ingredient_id: row.ingredient_id,
    name: row.name,
    category: row.category,
    calories_per_100g: toInteger(row.calories_per_100g),
    kj_per_100g: toInteger(row.kj_per_100g)
});

// ===========================================================================
// 3. IMPORT CATEGORY NODES
// ===========================================================================
LOAD CSV WITH HEADERS FROM "file:///final_categories.csv" AS row
CREATE (:Category {
    category_id: row.category_id,
    name: row.name,
    type: row.type
});

// ===========================================================================
// 4. CREATE RECIPE-INGREDIENT RELATIONSHIPS (CONTAINS)
// ===========================================================================
LOAD CSV WITH HEADERS FROM "file:///final_recipe_ingredient_rels.csv" AS row
MATCH (r:Recipe {recipe_id: row.recipe_id})
MATCH (i:Ingredient {ingredient_id: row.ingredient_id})
CREATE (r)-[:CONTAINS]->(i);

// ===========================================================================
// 5. CREATE RECIPE-CATEGORY RELATIONSHIPS (BELONGS_TO)
// ===========================================================================
LOAD CSV WITH HEADERS FROM "file:///final_recipe_category_rels.csv" AS row
MATCH (r:Recipe {recipe_id: row.recipe_id})
MATCH (c:Category {category_id: row.category_id})
CREATE (r)-[:BELONGS_TO]->(c);

// ===========================================================================
// 6. CREATE INGREDIENT-CATEGORY RELATIONSHIPS (CLASSIFIED_AS)
// ===========================================================================
LOAD CSV WITH HEADERS FROM "file:///final_ingredient_category_rels.csv" AS row
MATCH (i:Ingredient {ingredient_id: row.ingredient_id})
MATCH (c:Category {category_id: row.category_id})
CREATE (i)-[:CLASSIFIED_AS]->(c);

// ===========================================================================
// 7. CREATE ADDITIONAL INDEXES FOR PERFORMANCE
// ===========================================================================
CREATE INDEX recipe_title_index IF NOT EXISTS FOR (r:Recipe) ON (r.title);
CREATE INDEX ingredient_name_index IF NOT EXISTS FOR (i:Ingredient) ON (i.name);
CREATE INDEX category_name_index IF NOT EXISTS FOR (c:Category) ON (c.name);
CREATE INDEX recipe_rating_index IF NOT EXISTS FOR (r:Recipe) ON (r.rating);
CREATE INDEX recipe_calories_index IF NOT EXISTS FOR (r:Recipe) ON (r.calories);
CREATE INDEX ingredient_calories_index IF NOT EXISTS FOR (i:Ingredient) ON (i.calories_per_100g);

// ===========================================================================
// 8. CREATE DERIVED RELATIONSHIPS (SIMILAR_TO based on shared ingredients)
// ===========================================================================
// Create relationships between recipes that share many ingredients
MATCH (r1:Recipe)-[:CONTAINS]->(i:Ingredient)<-[:CONTAINS]-(r2:Recipe)
WHERE r1.recipe_id < r2.recipe_id  // Avoid duplicate relationships
WITH r1, r2, COUNT(i) as shared_ingredients
WHERE shared_ingredients >= 3  // Recipes with 3+ shared ingredients are similar
CREATE (r1)-[:SIMILAR_TO {shared_ingredients: shared_ingredients}]->(r2);

// ===========================================================================
// 9. VERIFICATION QUERIES
// ===========================================================================
// Count nodes
MATCH (r:Recipe) RETURN "Recipes" as Node_Type, COUNT(r) as Count
UNION
MATCH (i:Ingredient) RETURN "Ingredients" as Node_Type, COUNT(i) as Count
UNION
MATCH (c:Category) RETURN "Categories" as Node_Type, COUNT(c) as Count;

// Count relationships
MATCH ()-[rel:CONTAINS]->() RETURN "CONTAINS" as Relationship_Type, COUNT(rel) as Count
UNION
MATCH ()-[rel:BELONGS_TO]->() RETURN "BELONGS_TO" as Relationship_Type, COUNT(rel) as Count
UNION
MATCH ()-[rel:CLASSIFIED_AS]->() RETURN "CLASSIFIED_AS" as Relationship_Type, COUNT(rel) as Count
UNION
MATCH ()-[rel:SIMILAR_TO]->() RETURN "SIMILAR_TO" as Relationship_Type, COUNT(rel) as Count;

// ===========================================================================
// 10. SAMPLE QUERIES FOR TESTING
// ===========================================================================

// Find top 10 highest rated recipes
// MATCH (r:Recipe) WHERE r.rating > 0 RETURN r.title, r.rating ORDER BY r.rating DESC LIMIT 10;

// Find all recipes containing "chicken"
// MATCH (r:Recipe)-[:CONTAINS]->(i:Ingredient) WHERE i.name CONTAINS "chicken" RETURN DISTINCT r.title LIMIT 10;

// Find recipes in "Dessert" category
// MATCH (r:Recipe)-[:BELONGS_TO]->(c:Category) WHERE c.name CONTAINS "Dessert" RETURN r.title LIMIT 10;

// Find ingredients with highest calories
// MATCH (i:Ingredient) WHERE i.calories_per_100g > 0 RETURN i.name, i.calories_per_100g ORDER BY i.calories_per_100g DESC LIMIT 10;

// Find recipes similar to a specific recipe (by shared ingredients)
// MATCH (r:Recipe {title: "Chocolate Chip Cookies"})-[:SIMILAR_TO]-(similar:Recipe) RETURN similar.title, similar.rating;

// Complex query: Find healthy vegetarian recipes (low calories, high protein)
// MATCH (r:Recipe)-[:BELONGS_TO]->(c:Category) 
// WHERE c.name CONTAINS "Vegetarian" AND r.calories < 300 AND r.protein > 10
// RETURN r.title, r.calories, r.protein ORDER BY r.rating DESC LIMIT 5;