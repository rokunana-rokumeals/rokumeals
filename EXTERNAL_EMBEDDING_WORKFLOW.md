# External Embedding Generation Workflow

## Overview
Generate embeddings di environment terpisah (Colab, server lain, dll) kemudian integrate ke Django project. Workflow ini menghindari masalah encoding, memory, dan dependency conflicts.

## Setup External Environment

### 1. Install Dependencies
```bash
pip install torch transformers sentence-transformers accelerate safetensors
pip install numpy tqdm
```

### 2. Environment Requirements
- Python 3.8+
- CUDA (optional, untuk GPU acceleration)
- Minimal 8GB RAM (16GB recommended untuk dataset besar)

## Step-by-Step Workflow

### Step 1: Export Data dari Django
```bash
# Export semua data
python manage.py export_data_for_embeddings

# Export dengan limit (untuk testing)
python manage.py export_data_for_embeddings --limit 100

# Export ke format CSV
python manage.py export_data_for_embeddings --format csv --output-dir embedding_export
```

**Output files:**
- `embedding_data/recipes.json` - Data resep untuk embedding
- `embedding_data/ingredients.json` - Data ingredient
- `embedding_data/categories.json` - Data kategori

### Step 2: Transfer ke External Environment
```bash
# Copy files ke environment external (Colab/server)
# Bisa via Google Drive, SSH, atau upload manual
```

### Step 3: Generate Embeddings
```bash
# Di environment external
python external_embedding_generator.py

# Dengan custom settings
python external_embedding_generator.py \
    --input-dir embedding_data \
    --output-dir embeddings_output \
    --batch-size 16 \
    --model Qwen/Qwen3-Embedding-0.6B
```

**Output files:**
- `embeddings_output/embeddings_recipes.json`
- `embeddings_output/embeddings_ingredients.json`
- `embeddings_output/embeddings_categories.json`

### Step 4: Transfer Back & Import
```bash
# Copy embedding files back ke Django project
# Kemudian import ke database

# Dry run untuk preview
python manage.py import_embeddings --embedding-file embeddings_recipes.json --dry-run

# Import actual
python manage.py import_embeddings --embedding-file embeddings_recipes.json
python manage.py import_embeddings --embedding-file embeddings_ingredients.json
python manage.py import_embeddings --embedding-file embeddings_categories.json
```

## Google Colab Example

### Notebook Setup
```python
# Install dependencies
!pip install torch transformers sentence-transformers accelerate safetensors

# Upload exported data files
from google.colab import files
uploaded = files.upload()  # Upload recipes.json, ingredients.json, categories.json

# Download the generator script
!wget https://your-repo/external_embedding_generator.py

# Run embedding generation
!python external_embedding_generator.py --input-dir . --output-dir embeddings

# Download embeddings
files.download('embeddings/embeddings_recipes.json')
files.download('embeddings/embeddings_ingredients.json') 
files.download('embeddings/embeddings_categories.json')
```

## File Formats

### Export Data Format
```json
{
  "id": "recipe-123",
  "type": "recipe", 
  "text": "Nasi Goreng. Delicious Indonesian fried rice. Ingredients: rice, eggs, soy sauce. Categories: main course, indonesian.",
  "title": "Nasi Goreng",
  "description": "Delicious Indonesian fried rice",
  "ingredients": "rice, eggs, soy sauce",
  "categories": "main course, indonesian"
}
```

### Embeddings Output Format
```json
{
  "id": "recipe-123",
  "type": "recipe",
  "text": "Nasi Goreng. Delicious Indonesian fried rice...",
  "embedding": [0.1234, -0.5678, 0.9012, ...] // 1024 dimensions
}
```

## Performance Optimization

### Batch Size Guidelines
- **CPU**: 8-16 items per batch
- **GPU (8GB)**: 32-64 items per batch  
- **GPU (16GB+)**: 64-128 items per batch

### Memory Management
```python
# Clear cache between batches
import torch
torch.cuda.empty_cache()

# Use mixed precision
model = model.half()  # FP16 untuk GPU memory efficiency
```

## Troubleshooting

### Common Issues

**1. CUDA Out of Memory**
```python
# Reduce batch size
--batch-size 8

# Use CPU fallback
export CUDA_VISIBLE_DEVICES=""
```

**2. Encoding Errors**
```python
# Files sudah handle UTF-8, tapi jika masih error:
with open(file, 'r', encoding='utf-8', errors='ignore') as f:
    data = json.load(f)
```

**3. Model Download Failed**
```python
# Manual download
from transformers import AutoModel, AutoTokenizer
model = AutoModel.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
```

## Verification Steps

### 1. Check Export
```bash
python manage.py export_data_for_embeddings --limit 5
# Verify files created and readable
```

### 2. Test Generation
```python
# Test with small batch first
python external_embedding_generator.py --input-dir test_data --batch-size 2
```

### 3. Validate Import
```bash
# Dry run first
python manage.py import_embeddings --embedding-file test_embeddings.json --dry-run
```

### 4. Test Search
```bash
# After import, test semantic search
curl "http://localhost:8000/api/semantic-search/?q=nasi goreng&type=recipe"
```

## Integration dengan Existing Features

Setelah import embeddings berhasil:

1. **Vector indexes otomatis terdeteksi** - Neo4j akan recognize embedding fields
2. **Semantic search API langsung aktif** - Endpoints sudah siap
3. **Frontend toggle berfungsi** - User bisa switch semantic/keyword search
4. **Similar items otomatis muncul** - Di halaman detail

## Benefits External Generation

1. **No Environment Conflicts** - Isolasi dependency issues
2. **Scalable Processing** - Bisa pakai GPU server dedicated
3. **Resumable Process** - Bisa pause/resume generation
4. **Resource Optimization** - Tidak load Django environment
5. **Easy Debugging** - Focused environment untuk troubleshooting

Workflow ini memberikan fleksibilitas maksimal sambil maintain compatibility dengan existing codebase!