"""
Lightweight semantic search implementation using imported embeddings
This module handles semantic search after embeddings are imported via external generation
"""
import json
import logging
from typing import List, Dict, Optional
from neomodel import db

logger = logging.getLogger(__name__)

class SimpleSemanticSearch:
    """
    Simple semantic search using imported embeddings and Neo4j queries
    No heavy dependencies - just uses the embeddings that were imported
    """
    
    @staticmethod
    def has_embeddings(node_type: str = 'recipe') -> bool:
        """
        Check if embeddings are available in the database
        
        Args:
            node_type: Type of node to check ('recipe', 'ingredient', 'category')
        
        Returns:
            True if embeddings are available
        """
        try:
            node_label = node_type.capitalize()
            query = f"""
            MATCH (n:{node_label})
            WHERE n.embedding IS NOT NULL AND n.embedding <> ''
            RETURN count(n) as count
            LIMIT 1
            """
            results, _ = db.cypher_query(query)
            return results[0][0] > 0
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
                WHERE n.embedding IS NOT NULL AND n.embedding <> ''
                RETURN count(n) as with_embeddings,
                       count(*) as total
                """
                results, _ = db.cypher_query(query)
                with_emb, total = results[0]
                stats[node_type] = {
                    'with_embeddings': with_emb,
                    'total': total,
                    'percentage': round((with_emb / total * 100) if total > 0 else 0, 1)
                }
            except Exception as e:
                logger.error(f"Error getting stats for {node_type}: {e}")
                stats[node_type] = {'error': str(e)}
        
        return stats
    
    @staticmethod
    def search_by_embedding(query_embedding: List[float], 
                          node_type: str = 'recipe',
                          limit: int = 20,
                          threshold: float = 0.7) -> List[Dict]:
        """
        Search using vector similarity with imported embeddings
        
        Args:
            query_embedding: The query embedding vector
            node_type: Type of nodes to search
            limit: Maximum results to return
            threshold: Minimum similarity threshold
        
        Returns:
            List of similar nodes with similarity scores
        """
        try:
            node_label = node_type.capitalize()
            
            # Use Neo4j's cosine similarity for vector search
            query = f"""
            MATCH (n:{node_label})
            WHERE n.embedding IS NOT NULL AND n.embedding <> ''
            WITH n, gds.similarity.cosine(
                $query_embedding, 
                [x IN apoc.convert.fromJsonList(n.embedding) | toFloat(x)]
            ) AS similarity
            WHERE similarity >= $threshold
            RETURN n.id as id,
                   n.title as title,
                   n.name as name,
                   n.description as description,
                   similarity
            ORDER BY similarity DESC
            LIMIT $limit
            """
            
            results, _ = db.cypher_query(query, {
                'query_embedding': query_embedding,
                'threshold': threshold,
                'limit': limit
            })
            
            formatted_results = []
            for result in results:
                node_id, title, name, description, similarity = result
                formatted_results.append({
                    'id': node_id,
                    'title': title or name,
                    'description': description,
                    'type': node_type,
                    'similarity_score': round(float(similarity), 3)
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    @staticmethod
    def find_similar_items(item_id: str, 
                          item_type: str,
                          limit: int = 5,
                          threshold: float = 0.7) -> List[Dict]:
        """
        Find items similar to a given item using its embedding
        
        Args:
            item_id: ID of the reference item
            item_type: Type of item ('recipe', 'ingredient', 'category')
            limit: Maximum results
            threshold: Minimum similarity threshold
        
        Returns:
            List of similar items
        """
        try:
            node_label = item_type.capitalize()
            
            # Get the embedding of the reference item
            query = f"""
            MATCH (ref:{node_label} {{id: $item_id}})
            WHERE ref.embedding IS NOT NULL AND ref.embedding <> ''
            RETURN ref.embedding as embedding
            """
            
            results, _ = db.cypher_query(query, {'item_id': item_id})
            
            if not results:
                return []
            
            ref_embedding = json.loads(results[0][0])
            
            # Find similar items
            return SimpleSemanticSearch.search_by_embedding(
                ref_embedding, item_type, limit, threshold
            )
            
        except Exception as e:
            logger.error(f"Error finding similar items: {e}")
            return []

# Global instance for easy import
simple_semantic_search = SimpleSemanticSearch()