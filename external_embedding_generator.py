"""
External Embedding Generation Script
Generate embeddings using Qwen3-Embedding-0.6B in external environment
"""

import json
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from tqdm import tqdm
import argparse
import os

class QwenEmbeddingGenerator:
    def __init__(self, model_name="Qwen/Qwen3-Embedding-0.6B", device=None):
        """
        Initialize Qwen embedding generator
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to run on (auto-detected if None)
        """
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        
        print(f"Loading {model_name} on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(
            model_name, 
            trust_remote_code=True,
            torch_dtype=torch.float32
        ).to(self.device)
        
        self.model.eval()
        print("Model loaded successfully!")

    def get_detailed_instruct(self, task_description: str, query: str) -> str:
        """Create instruction-aware query for better embeddings"""
        return f'Instruct: {task_description}\nQuery: {query}'

    def _last_token_pool(self, last_hidden_states, attention_mask):
        """Extract embeddings from last token"""
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

    def generate_embedding(self, text: str, task_description: str = None) -> list:
        """
        Generate embedding for given text
        
        Args:
            text: Input text
            task_description: Task description for instruction-aware embedding
            
        Returns:
            List of float values representing embedding
        """
        try:
            # Use instruction if provided
            if task_description:
                instructed_text = self.get_detailed_instruct(task_description, text)
            else:
                instructed_text = text
            
            # Tokenize
            batch_dict = self.tokenizer(
                instructed_text,
                max_length=512,
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            
            # Move to device
            batch_dict = {k: v.to(self.device) for k, v in batch_dict.items()}
            
            # Generate embedding
            with torch.no_grad():
                outputs = self.model(**batch_dict)
                embeddings = self._last_token_pool(
                    outputs.last_hidden_state, 
                    batch_dict['attention_mask']
                )
            
            # Normalize
            embeddings = F.normalize(embeddings, p=2, dim=1)
            
            return embeddings[0].cpu().tolist()
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

def process_data_file(generator, input_file, output_file, batch_size=32):
    """
    Process exported data file and generate embeddings
    
    Args:
        generator: QwenEmbeddingGenerator instance
        input_file: Input JSON file with exported data
        output_file: Output file for embeddings
        batch_size: Batch size for processing
    """
    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Processing {len(data)} items from {input_file}")
    
    # Task descriptions for different types
    task_descriptions = {
        'recipe': "Given a recipe query, find similar recipes based on ingredients, cooking methods, and flavors",
        'ingredient': "Given an ingredient query, find similar ingredients based on nutritional content and culinary usage", 
        'category': "Given a category query, find similar categories based on food types and classifications"
    }
    
    embeddings_data = []
    
    # Process in batches
    for i in tqdm(range(0, len(data), batch_size), desc="Generating embeddings"):
        batch = data[i:i+batch_size]
        
        for item in batch:
            text = item['text']
            item_type = item['type']
            task_desc = task_descriptions.get(item_type, "Find similar items based on content and context")
            
            embedding = generator.generate_embedding(text, task_desc)
            
            if embedding is not None:
                embeddings_data.append({
                    'id': item['id'],
                    'type': item['type'],
                    'text': text,
                    'embedding': embedding
                })
            else:
                print(f"Failed to generate embedding for {item['type']} {item['id']}")
    
    # Save embeddings
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(embeddings_data)} embeddings to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Generate embeddings using Qwen3-Embedding-0.6B')
    parser.add_argument('--input-dir', default='embedding_data', help='Directory with exported data')
    parser.add_argument('--output-dir', default='embeddings_output', help='Output directory for embeddings')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for processing')
    parser.add_argument('--model', default='Qwen/Qwen3-Embedding-0.6B', help='Model name')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize generator
    generator = QwenEmbeddingGenerator(args.model)
    
    # Process each data file
    data_files = ['recipes.json', 'ingredients.json', 'categories.json']
    
    for data_file in data_files:
        input_path = os.path.join(args.input_dir, data_file)
        output_path = os.path.join(args.output_dir, f'embeddings_{data_file}')
        
        if os.path.exists(input_path):
            process_data_file(generator, input_path, output_path, args.batch_size)
        else:
            print(f"Skipping {input_path} - file not found")
    
    print("All embeddings generated successfully!")
    print(f"Files saved in {args.output_dir}/")
    print("Next steps:")
    print("1. Copy embedding files to your Django project")
    print("2. Run: python manage.py import_embeddings --embedding-file embeddings_recipes.json")
    print("3. Repeat for ingredients and categories")

if __name__ == "__main__":
    main()