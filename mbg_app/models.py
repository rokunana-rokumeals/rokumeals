"""
MBG Knowledge Graph Models using Neomodel
Models untuk Recipe, Ingredient, dan Category dengan relationships
"""
from neomodel import (
    StructuredNode, StringProperty, FloatProperty, IntegerProperty,
    RelationshipTo, RelationshipFrom, UniqueIdProperty
)

class Recipe(StructuredNode):
    """Recipe node dalam Knowledge Graph"""
    recipe_id = StringProperty(unique_index=True, required=True)
    title = StringProperty(required=True, index=True)
    rating = FloatProperty(default=0.0)
    calories = FloatProperty(default=0.0)
    protein = FloatProperty(default=0.0)
    fat = FloatProperty(default=0.0)
    sodium = FloatProperty(default=0.0)
    description = StringProperty()
    directions = StringProperty()
    ingredients_raw = StringProperty()
    
    # Relationships
    contains = RelationshipTo('Ingredient', 'CONTAINS')
    belongs_to = RelationshipTo('Category', 'BELONGS_TO')
    
    def __str__(self):
        return f"Recipe: {self.title}"
    
    @property
    def ingredient_count(self):
        """Count jumlah ingredients dalam recipe"""
        return len(self.contains.all())
    
    @property
    def categories_list(self):
        """List semua categories untuk recipe ini"""
        return [cat.name for cat in self.belongs_to.all()]


class Ingredient(StructuredNode):
    """Ingredient node dalam Knowledge Graph"""
    ingredient_id = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True, index=True)
    category = StringProperty(default='Unknown')
    calories_per_100g = IntegerProperty(default=0)
    kj_per_100g = IntegerProperty(default=0)
    
    # Enhanced nutritional data from DBpedia
    carbohydrates_g = FloatProperty()      # Carbohydrates per 100g
    fat_g = FloatProperty()                # Fat content per 100g  
    protein_g = FloatProperty()            # Protein per 100g
    energy_kcal = FloatProperty()          # Energy in kcal
    fiber_g = FloatProperty()              # Dietary fiber per 100g
    sugar_g = FloatProperty()              # Sugar content per 100g
    
    # Vitamins (mg/μg per 100g)
    vitamin_c_mg = FloatProperty()         # Vitamin C in mg
    vitamin_a_ug = FloatProperty()         # Vitamin A in μg
    vitamin_b6_mg = FloatProperty()        # Vitamin B6 in mg
    
    # Minerals (mg per 100g)
    calcium_mg = FloatProperty()           # Calcium content
    iron_mg = FloatProperty()              # Iron content
    sodium_mg = FloatProperty()            # Sodium content
    potassium_mg = FloatProperty()         # Potassium content
    magnesium_mg = FloatProperty()         # Magnesium content
    zinc_mg = FloatProperty()              # Zinc content
    
    # DBpedia metadata
    dbpedia_uri = StringProperty()         # DBpedia resource URI
    dbpedia_label = StringProperty()       # DBpedia label
    enriched_at = StringProperty()         # Timestamp of enrichment
    
    # Relationships
    used_in = RelationshipFrom('Recipe', 'CONTAINS')
    classified_as = RelationshipTo('Category', 'CLASSIFIED_AS')
    
    def __str__(self):
        return f"Ingredient: {self.name}"
    
    @property
    def recipe_count(self):
        """Count berapa recipe menggunakan ingredient ini"""
        return len(self.used_in.all())
    
    @property
    def is_enriched(self):
        """Check if ingredient has been enriched with DBpedia data"""
        return bool(self.dbpedia_uri)
    
    @property
    def nutritional_completeness(self):
        """Calculate percentage of nutritional data available (0-100)"""
        nutritional_fields = [
            'carbohydrates_g', 'fat_g', 'protein_g', 'energy_kcal', 'fiber_g', 'sugar_g',
            'vitamin_c_mg', 'vitamin_a_ug', 'vitamin_b6_mg', 
            'calcium_mg', 'iron_mg', 'sodium_mg', 'potassium_mg', 'magnesium_mg', 'zinc_mg'
        ]
        
        filled_fields = sum(1 for field in nutritional_fields if getattr(self, field, None) is not None)
        return (filled_fields / len(nutritional_fields)) * 100
    
    def get_nutritional_summary(self):
        """Get a summary of available nutritional data"""
        summary = {}
        
        # Macronutrients
        if self.carbohydrates_g: summary['Carbohydrates'] = f"{self.carbohydrates_g}g"
        if self.protein_g: summary['Protein'] = f"{self.protein_g}g"
        if self.fat_g: summary['Fat'] = f"{self.fat_g}g"
        if self.energy_kcal: summary['Energy'] = f"{self.energy_kcal} kcal"
        if self.fiber_g: summary['Fiber'] = f"{self.fiber_g}g"
        
        # Key vitamins
        if self.vitamin_c_mg: summary['Vitamin C'] = f"{self.vitamin_c_mg}mg"
        if self.vitamin_a_ug: summary['Vitamin A'] = f"{self.vitamin_a_ug}μg"
        
        # Key minerals  
        if self.calcium_mg: summary['Calcium'] = f"{self.calcium_mg}mg"
        if self.iron_mg: summary['Iron'] = f"{self.iron_mg}mg"
        if self.potassium_mg: summary['Potassium'] = f"{self.potassium_mg}mg"
        
        return summary


class Category(StructuredNode):
    """Category node untuk klasifikasi Recipe dan Ingredient"""
    category_id = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True, index=True)
    type = StringProperty(required=True)  # 'recipe' or 'ingredient'
    
    # Relationships
    has_recipes = RelationshipFrom('Recipe', 'BELONGS_TO')
    has_ingredients = RelationshipFrom('Ingredient', 'CLASSIFIED_AS')
    
    def __str__(self):
        return f"Category: {self.name} ({self.type})"
    
    @property
    def item_count(self):
        """Count jumlah items dalam category ini"""
        if self.type == 'recipe':
            return len(self.has_recipes.all())
        else:
            return len(self.has_ingredients.all())


class SearchMixin:
    """Mixin untuk search functionality across models"""
    
    @classmethod
    def search_by_name(cls, query, limit=20):
        """Search nodes berdasarkan nama dengan fuzzy matching"""
        if not query:
            return []
            
        # Case-insensitive search dengan CONTAINS
        if hasattr(cls, 'title'):  # Recipe
            results = cls.nodes.filter(title__icontains=query)[:limit]
        elif hasattr(cls, 'name'):  # Ingredient, Category
            results = cls.nodes.filter(name__icontains=query)[:limit]
        else:
            results = []
            
        return list(results)
    
    @classmethod  
    def get_all_paginated(cls, page=1, per_page=20):
        """Get semua nodes dengan pagination"""
        skip = (page - 1) * per_page
        return cls.nodes.all()[skip:skip + per_page]


# Add SearchMixin ke models
Recipe.__bases__ = (StructuredNode, SearchMixin)
Ingredient.__bases__ = (StructuredNode, SearchMixin)
Category.__bases__ = (StructuredNode, SearchMixin)
