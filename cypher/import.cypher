MATCH (n) DETACH DELETE n;

LOAD CSV WITH HEADERS FROM "file:///recipes.csv" AS row
MERGE (r:Recipe {title: row.title})
SET r.rating = toFloat(row.rating),
    r.calories = toInteger(row.calories),
    r.protein = toInteger(row.protein),
    r.fat = toInteger(row.fat),
    r.sodium = toInteger(row.sodium),
    r.desc = row.desc,
    r.directions = row.directions,
    r.ingredients_raw = row.ingredients_raw;

LOAD CSV WITH HEADERS FROM "file:///recipe_categories.csv" AS row
MERGE (c:RecipeCategory {name: row.category})
WITH row, c
MATCH (r:Recipe {title: row.title})
MERGE (r)-[:HAS_RECIPE_CATEGORY]->(c);

LOAD CSV WITH HEADERS FROM "file:///ingredients.csv" AS row
MERGE (i:Ingredient {name: row.Ingredient});

LOAD CSV WITH HEADERS FROM "file:///recipe_ingredients.csv" AS row
MATCH (r:Recipe {title: row.title})
MATCH (i:Ingredient {name: row.ingredient_clean})
MERGE (r)-[:HAS_INGREDIENT]->(i);

LOAD CSV WITH HEADERS FROM "file:///ingredient_categories.csv" AS row
MERGE (c:IngredientCategory {name: row.Category})
WITH row, c
MATCH (i:Ingredient {name: row.Ingredient})
MERGE (i)-[:HAS_INGREDIENT_CATEGORY]->(c);

LOAD CSV WITH HEADERS FROM "file:///ingredient_calories.csv" AS row
MERGE (ic:IngredientCalories {name: row.Ingredient})
SET ic.per100grams = row.per100grams,
    ic.cal100g = toInteger(replace(row.Cals_per100grams, " cal", "")),
    ic.kj100g = toInteger(replace(row.KJ_per100grams, " kJ", ""))
WITH row
MATCH (i:Ingredient {name: row.Ingredient})
MATCH (ic:IngredientCalories {name: row.Ingredient})
MERGE (i)-[:HAS_CALORIES]->(ic);
