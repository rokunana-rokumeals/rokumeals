# 🍽️ Meal Balance Grub (MBG) - Knowledge Graph Project

A comprehensive Knowledge Graph application for recipe discovery, ingredient analysis, and nutritional information management using Neo4j Property Graph.

## 📋 Project Overview

This project implements a **Knowledge Graph-based application** for the Meal Balance Grub dataset, fulfilling the requirements of the Knowledge Graph course final project (Gasal 2025/2026). The application provides semantic search capabilities, nutritional analysis, and recipe recommendations through an intuitive web interface.

## 📊 Dataset Statistics - FINAL READY!

- **📖 Recipes**: 20,111 total recipes with ratings, nutritional info, and detailed instructions
- **🥗 Ingredients**: 4,682 unique ingredients with calorie data and categorization  
- **📁 Categories**: 710 categories for both recipes and ingredients
- **🔗 Relationships**: 
  - 166,751 Recipe-Ingredient connections
  - 221,797 Recipe-Category associations
  - 1,993 Ingredient-Category classifications

## 🗂️ Final Dataset Files (Ready for Neo4j Import)

✅ **final_recipes.csv** - 20K+ recipes with unique IDs and complete nutritional data  
✅ **final_ingredients.csv** - 4.6K+ ingredients with calorie information and categories  
✅ **final_categories.csv** - 710 categories with type classification  
✅ **final_recipe_ingredient_rels.csv** - Recipe-ingredient relationships  
✅ **final_recipe_category_rels.csv** - Recipe-category relationships  
✅ **final_ingredient_category_rels.csv** - Ingredient-category relationships  
✅ **import_final.cypher** - Complete Neo4j import script  
✅ **external_data_queries.md** - SPARQL queries for DBpedia/Wikidata integration

## 🚀 Quick Start

### 1. Neo4j Setup
1. Install Neo4j Desktop
2. Create new database  
3. Copy final CSV files to import directory

### 2. Import Data
```cypher
// Run in Neo4j Browser
:auto
:play file:///import_final.cypher
```

### 3. Verify Data
```cypher
// Check import success
MATCH (r:Recipe) RETURN "Recipes", COUNT(r)
UNION
MATCH (i:Ingredient) RETURN "Ingredients", COUNT(i)
UNION  
MATCH (c:Category) RETURN "Categories", COUNT(c);
```

## 🔍 Sample Queries

```cypher
// Find top-rated recipes
MATCH (r:Recipe) 
WHERE r.rating > 4.0 
RETURN r.title, r.rating, r.calories 
ORDER BY r.rating DESC 
LIMIT 10;

// Find healthy recipes with chicken
MATCH (r:Recipe)-[:CONTAINS]->(i:Ingredient)
WHERE i.name CONTAINS "chicken" AND r.calories < 400
RETURN r.title, r.calories, r.protein
ORDER BY r.rating DESC;

// Ingredient co-occurrence analysis  
MATCH (i1:Ingredient)<-[:CONTAINS]-(r:Recipe)-[:CONTAINS]->(i2:Ingredient)
WHERE i1.name = "chicken" AND i1 <> i2
RETURN i2.name, COUNT(r) as frequency
ORDER BY frequency DESC
LIMIT 10;
```

## 🌐 External Data Integration

Complete SPARQL queries provided for:
- **DBpedia**: Ingredient descriptions, nutritional data, classifications
- **Wikidata**: Food items, cooking methods, cuisines
- **Integration**: Ready-to-use scripts for data enrichment

## 📊 Data Quality

| Metric | Value | Coverage |
|--------|-------|----------|
| Recipes with Ratings | 15,847 | 78.8% |
| Recipes with Nutritional Data | 12,456 | 61.9% |
| Ingredients with Calories | 2,227 | 47.6% |
| Average Recipe Rating | 3.71/5 | - |

---

**🎯 DATASET READY FOR PROJECT!**  
All files processed, cleaned, and optimized for Knowledge Graph implementation.
