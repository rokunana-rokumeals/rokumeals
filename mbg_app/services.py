import logging
import os
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

class GeminiEmbeddingService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_id = "models/text-embedding-004"
        
        if not self.api_key:
            logger.error("GEMINI_API_KEY is missing from environment variables.")
        else:
            try:
                genai.configure(api_key=self.api_key)
                logger.info(f"Gemini Embedding Service initialized with {self.model_id}")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")

    def generate_embedding(self, text: str, node_type: str = 'recipe') -> list:
        """
        Generate 768-dim Gemini embeddings.
        Args:
            text: The text to embed
            node_type: (Optional) Used for task hinting if supported, mostly ignored by this specific model call but kept for compatibility.
        """
        if not self.api_key:
            logger.error("Gemini API key not found.")
            return None

        try:
            # Task type helps Gemini optimize the vector for retrieval
            response = genai.embed_content(
                model=self.model_id,
                content=text,
                task_type="retrieval_query" 
            )
            
            # Returns a list of floats (768 dimensions)
            return response["embedding"]
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return None

# Global instance
embedding_service = GeminiEmbeddingService.get_instance()