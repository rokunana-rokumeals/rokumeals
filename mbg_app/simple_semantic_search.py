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
        """
        try:
            # DEBUG: Print dimensions
            print(f"DEBUG: Query Vector Length: {len(query_embedding)}")
            
            node_label = node_type.capitalize()
            
            # Using manual Cosine Similarity query
            # We explicitly return specific ID/Name fields to handle different node types
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
                # Unpack the polymorphic return fields
                r_id, i_id, c_id, title, name, desc, score = row
                
                # Determine the correct ID and Title based on what isn't None
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