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
    
    # Relationships
    used_in = RelationshipFrom('Recipe', 'CONTAINS')
    classified_as = RelationshipTo('Category', 'CLASSIFIED_AS')
    
    def __str__(self):
        return f"Ingredient: {self.name}"
    
    @property
    def recipe_count(self):
        """Count berapa recipe menggunakan ingredient ini"""
        return len(self.used_in.all())


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
