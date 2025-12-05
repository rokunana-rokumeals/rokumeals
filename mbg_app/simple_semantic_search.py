import logging
import json
from typing import List, Dict
from neomodel import db

logger = logging.getLogger(__name__)

class SimpleSemanticSearch:
    """
    Semantic search implementation using Gemini embeddings and Neo4j.
    """
    
    @staticmethod
    def has_embeddings(node_type: str = 'recipe') -> bool:
        """Check if embeddings are available in the database"""
        try:
            node_label = node_type.capitalize()
            query = f"""
            MATCH (n:{node_label})
            WHERE n.embedding IS NOT NULL AND size(n.embedding) > 0
            RETURN count(n) > 0
            """
            results, _ = db.cypher_query(query)
            return results[0][0]
        except Exception as e:
            logger.error(f"Error checking embeddings: {e}")
            return False

    @staticmethod
    def get_embedding_stats() -> Dict:
        """Get statistics about available embeddings"""
        stats = {}
        for node_type in ['recipe', 'ingredient', 'category']:
            try:
                node_label = node_type.capitalize()
                query = f"""
                MATCH (n:{node_label})
                WHERE n.embedding IS NOT NULL
                RETURN count(n) as with_embeddings, count(*) as total
                """
                results, _ = db.cypher_query(query)
                with_emb, total = results[0]
                stats[node_type] = {
                    'with_embeddings': with_emb,
                    'total': total,
                    'percentage': round((with_emb / total * 100) if total > 0 else 0, 1)
                }
            except Exception:
                stats[node_type] = {'error': 'Could not fetch stats'}
        return stats

    @staticmethod
    def search_by_embedding(query_embedding: list, node_type: str = 'recipe', limit: int = 20, threshold: float = 0.5) -> List[Dict]:
        """
        Perform vector search using direct float-list vectors in Neo4j (Manual Cosine).
        Enhanced to include all fields needed by UI.
        """
        try:
            # DEBUG: Print dimensions
            print(f"DEBUG: Query Vector Length: {len(query_embedding)}")
            
            node_label = node_type.capitalize()
            
            # Enhanced queries to match regular search data structure
            if node_type == 'recipe':
                cypher = f"""
                MATCH (n:{node_label})
                WHERE n.embedding IS NOT NULL
                WITH n, gds.similarity.cosine($query_embedding, n.embedding) AS similarity
                WHERE similarity >= $threshold
                OPTIONAL MATCH (n)-[:CONTAINS]->(i:Ingredient)
                OPTIONAL MATCH (n)-[:BELONGS_TO]->(c:Category)
                WITH n, similarity, count(DISTINCT i) as ingredient_count, collect(DISTINCT c.name) as categories
                RETURN n.recipe_id as id, n.title as title, n.rating as rating, n.calories as calories,
                       n.description as description, ingredient_count, categories, similarity
                ORDER BY similarity DESC
                LIMIT $limit
                """
            elif node_type == 'ingredient':
                cypher = f"""
                MATCH (n:{node_label})
                WHERE n.embedding IS NOT NULL
                WITH n, gds.similarity.cosine($query_embedding, n.embedding) AS similarity
                WHERE similarity >= $threshold
                OPTIONAL MATCH (n)<-[:CONTAINS]-(r:Recipe)
                WITH n, similarity, count(DISTINCT r) as recipe_count
                RETURN n.ingredient_id as id, n.name as name, n.category as category,
                       n.calories_per_100g as calories_per_100g, recipe_count, similarity
                ORDER BY similarity DESC
                LIMIT $limit
                """
            elif node_type == 'category':
                cypher = f"""
                MATCH (n:{node_label})
                WHERE n.embedding IS NOT NULL
                WITH n, gds.similarity.cosine($query_embedding, n.embedding) AS similarity
                WHERE similarity >= $threshold
                OPTIONAL MATCH (n)<-[:BELONGS_TO]-(r:Recipe)
                OPTIONAL MATCH (n)<-[:CLASSIFIED_AS]-(i:Ingredient)
                WITH n, similarity, count(DISTINCT r) + count(DISTINCT i) as item_count
                RETURN n.category_id as id, n.name as name, n.type as category_type, item_count, similarity
                ORDER BY similarity DESC
                LIMIT $limit
                """
            else:
                # Fallback to original query for unknown types
                cypher = f"""
                MATCH (n:{node_label})
                WHERE n.embedding IS NOT NULL
                WITH n, gds.similarity.cosine($query_embedding, n.embedding) AS similarity
                WHERE similarity >= $threshold
                RETURN n.recipe_id, n.ingredient_id, n.category_id, 
                       n.title, n.name, n.description, similarity
                ORDER BY similarity DESC
                LIMIT $limit
                """

            results, _ = db.cypher_query(cypher, {
                "query_embedding": query_embedding,
                "limit": limit,
                "threshold": threshold
            })
            
            # DEBUG: Print result count
            print(f"DEBUG: Found {len(results)} matches for {node_type}")

            formatted_results = []
            for row in results:
                if node_type == 'recipe':
                    # Unpack recipe fields
                    recipe_id, title, rating, calories, description, ing_count, categories, score = row
                    # Handle description truncation
                    desc_display = description[:200] + '...' if description and len(description) > 200 else (description or '')
                    formatted_results.append({
                        'type': 'recipe',
                        'id': recipe_id,
                        'title': title,
                        'rating': rating or 0,
                        'calories': calories or 0,
                        'description': desc_display,
                        'ingredient_count': ing_count,
                        'categories': categories or [],
                        'similarity_score': round(float(score), 3)
                    })
                elif node_type == 'ingredient':
                    # Unpack ingredient fields  
                    ing_id, name, category, calories, rec_count, score = row
                    formatted_results.append({
                        'type': 'ingredient',
                        'id': ing_id,
                        'name': name,
                        'category': category or 'Unknown',
                        'calories_per_100g': calories or 0,
                        'recipe_count': rec_count,
                        'similarity_score': round(float(score), 3)
                    })
                elif node_type == 'category':
                    # Unpack category fields
                    cat_id, name, cat_type, item_count, score = row
                    formatted_results.append({
                        'type': 'category',
                        'id': cat_id,
                        'name': name,
                        'category_type': cat_type or 'Unknown',
                        'item_count': item_count,
                        'similarity_score': round(float(score), 3)
                    })
                else:
                    # Fallback for unknown types (original format)
                    r_id, i_id, c_id, title, name, desc, score = row
                    final_id = r_id or i_id or c_id
                    final_title = title or name
                    formatted_results.append({
                        'id': final_id,
                        'title': final_title,
                        'description': desc,
                        'type': node_type,
                        'similarity_score': round(float(score), 3)
                    })
            
            return formatted_results

        except Exception as e:
            # CRITICAL: Print the actual error to your terminal so you can see it in logs
            print(f"CRITICAL SEARCH ERROR: {e}")
            logger.error(f"Error in semantic search: {e}")
            return []

    @staticmethod
    def find_similar_items(item_id: str, item_type: str, limit: int = 5, threshold: float = 0.5) -> List[Dict]:
        """Find similar nodes given a reference node ID."""
        try:
            node_label = item_type.capitalize()
            id_field = f"{item_type}_id" # e.g. recipe_id
            
            # Fetch the embedding from the database
            cypher = f"""
            MATCH (n:{node_label} {{{id_field}: $ref_id}})
            RETURN n.embedding AS embedding
            """

            results, _ = db.cypher_query(cypher, {"ref_id": item_id})
            
            # Check if embedding exists
            if not results or not results[0][0]:
                return []

            ref_embedding = results[0][0] # this comes back as a list<float> from import_vectors

            return SimpleSemanticSearch.search_by_embedding(ref_embedding, item_type, limit, threshold)
            
        except Exception as e:
            logger.error(f"Error finding similar items: {e}")
            return []

# Global instance
simple_semantic_search = SimpleSemanticSearch()