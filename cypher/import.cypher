CREATE INDEX recipe_title IF NOT EXISTS FOR (r:Recipe) ON (r.title);
CREATE INDEX category_name IF NOT EXISTS FOR (c:Category) ON (c.name);
CREATE INDEX ingredient_name IF NOT EXISTS FOR (i:Ingredient) ON (i.name);

LOAD CSV WITH HEADERS FROM "file:///recipes.csv" AS row
MERGE (r:Recipe {title: row.title})
SET r.rating     = toFloat(row.rating),
    r.calories   = toInteger(row.calories),
    r.protein    = toInteger(row.protein),
    r.fat        = toInteger(row.fat),
    r.sodium     = toInteger(row.sodium),
    r.desc       = row.desc,
    r.directions = row.directions;


LOAD CSV WITH HEADERS FROM "file:///recipe_categories.csv" AS row
MATCH (r:Recipe {title: row.title})
MERGE (c:Category {name: row.category})
MERGE (r)-[:HAS_CATEGORY]->(c);

LOAD CSV WITH HEADERS FROM "file:///recipe_ingredients.csv" AS row
MATCH (r:Recipe {title: row.title})
MERGE (i:Ingredient {name: row.ingredient_raw})
MERGE (r)-[:HAS_INGREDIENT]->(i);
