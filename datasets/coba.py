import json
import pandas as pd
import re

# =============================================================================
# INGREDIENT PARSER
# =============================================================================

STOPWORDS = {
    "fresh", "freshly", "ground", "small", "large", "medium",
    "finely", "thinly", "sliced", "chopped", "diced", "crushed",
    "cup", "cups", "teaspoon", "tablespoon", "tsp", "tbsp",
    "oz", "ounce", "ounces", "pound", "pounds", "lb", "lbs",
    "head", "sprig", "stalk", "stalks", "clove", "cloves",
    "taste", "to", "or", "and"
}

COMMON_BIGRAMS = {
    "olive oil", "vegetable stock", "chicken stock", "soy sauce"
}

def clean_ingredient(raw):
    """Extract simplified ingredient keywords."""
    if not isinstance(raw, str):
        return ""

    text = raw.lower().strip()
    text = re.sub(r"\d+\/\d+|\d+", " ", text)        # remove numbers
    text = re.sub(r"[^\w\s]", " ", text)            # remove punctuation

    tokens = [t for t in text.split() if t not in STOPWORDS]
    if not tokens:
        return ""

    if len(tokens) >= 2:
        bigram = tokens[-2] + " " + tokens[-1]
        if bigram in COMMON_BIGRAMS:
            return bigram

    return tokens[-1]


# =============================================================================
# 1. LOAD EPICURIOUS JSON
# =============================================================================

with open("raw/full_format_recipes.json", "r", encoding="utf-8") as f:
    data_json = json.load(f)

recipes_rows = []
categories_rows = []
recipe_ing_rows = []

for r in data_json:

    title = r.get("title", "").strip()
    if title == "":
        continue  # skip invalid recipes

    # RAW INGREDIENTS → combined string with pipe separator
    raw_list = r.get("ingredients", []) or []
    raw_joined = " | ".join(raw_list)

    # Cleaned ingredient rows (recipe_ingredients.csv)
    for ing_raw in raw_list:
        recipe_ing_rows.append({
            "title": title,
            "ingredient_clean": clean_ingredient(ing_raw)
        })

    # Recipe categories
    for c in r.get("categories", []):
        categories_rows.append({
            "title": title,
            "category": c.strip()
        })

    # Recipe row (recipes.csv)
    recipes_rows.append({
        "title": title,
        "rating": r.get("rating", ""),
        "calories": r.get("calories", ""),
        "protein": r.get("protein", ""),
        "fat": r.get("fat", ""),
        "sodium": r.get("sodium", ""),
        "desc": r.get("desc", ""),
        "directions": "\n".join(r.get("directions", []) or []),
        "ingredients_raw": raw_joined
    })

recipes_df = pd.DataFrame(recipes_rows)
categories_df = pd.DataFrame(categories_rows)
recipe_ing_df = pd.DataFrame(recipe_ing_rows)


# =============================================================================
# 2. LOAD CALORIES.CSV
# =============================================================================

cal_df = pd.read_csv("raw/calories.csv")
cal_df["FoodItem"] = cal_df["FoodItem"].astype(str).str.strip()
cal_df["FoodCategory"] = cal_df["FoodCategory"].astype(str).str.strip()


# =============================================================================
# 3. BUILD ingredients.csv (UNION)
# =============================================================================

# Remove empty parsed ingredients
parsed_ing = set(
    ing for ing in recipe_ing_df["ingredient_clean"].dropna().unique()
    if isinstance(ing, str) and ing.strip() != ""
)

# Remove empty fooditems
fooditems = set(
    item for item in cal_df["FoodItem"].dropna().unique()
    if isinstance(item, str) and item.strip() != ""
)

# Final union
all_ingredients = sorted(parsed_ing.union(fooditems))
ingredients_df = pd.DataFrame({"Ingredient": all_ingredients})


# =============================================================================
# 4. ingredient_categories.csv
# =============================================================================

ingredient_categories_df = cal_df[["FoodItem", "FoodCategory"]].copy()
ingredient_categories_df.columns = ["Ingredient", "Category"]


# =============================================================================
# 5. ingredient_calories.csv
# =============================================================================

ingredient_calories_df = cal_df.copy()
ingredient_calories_df.rename(columns={"FoodItem": "Ingredient"}, inplace=True)


# =============================================================================
# SAVE ALL 6 CSV FILES
# =============================================================================

recipes_df.to_csv("recipes.csv", index=False)
categories_df.to_csv("recipe_categories.csv", index=False)
recipe_ing_df.to_csv("recipe_ingredients.csv", index=False)
ingredients_df.to_csv("ingredients.csv", index=False)
ingredient_categories_df.to_csv("ingredient_categories.csv", index=False)
ingredient_calories_df.to_csv("ingredient_calories.csv", index=False)

print("All 6 CSVs generated successfully!")
