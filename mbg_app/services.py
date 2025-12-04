import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenRouterEmbeddingService:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is missing!")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        
        # Exact model string used by OpenRouter
        self.model_id = "qwen/qwen3-embedding-0.6b"

    def generate_embedding(self, text: str, node_type: str = 'recipe') -> list[float] | None:
        task_descriptions = {
            'recipe': "Given a recipe query, find similar recipes based on ingredients, cooking methods, and flavors",
            'ingredient': "Given an ingredient query, find similar ingredients based on nutritional content and culinary usage",
            'category': "Given a category query, find similar categories based on food types and classifications"
        }
        
        task_desc = task_descriptions.get(node_type, "Find similar items based on content and context")
        instructed_text = f'Instruct: {task_desc}\nQuery: {text}'

        try:
            response = self.client.embeddings.create(
                model=self.model_id,
                input=instructed_text
            )
            return response.data[0].embedding   # → list[float] of length 1024
            
        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            return None


# Global singleton (same as yours)
embedding_service = OpenRouterEmbeddingService.get_instance()