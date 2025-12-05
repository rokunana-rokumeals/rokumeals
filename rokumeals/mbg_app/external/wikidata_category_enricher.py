"""
Wikidata Category Enricher
================================================================
Khusus untuk memperkaya data Kategori Resep (e.g. Vegetarian, Dinner, Italian).
Strategi: Adaptive Fetching dengan Keyword Filter khusus Kategori.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import logging
import re
from typing import Dict

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikidataCategoryEnricher:
    
    def __init__(self):
        self.sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.sparql.setReturnFormat(JSON)
        self.sparql.addCustomHttpHeader("User-Agent", "UniversityProject-KnowledgeGraph/4.0")
        self.sparql.setTimeout(20) 

    def clean_category_name(self, name: str) -> str:
        """
        Membersihkan nama kategori.
        Beda dengan ingredient, kita tidak hapus takaran (gram/oz).
        Kita hapus kata 'Recipe' atau 'Food' yang redundan.
        """
        clean_name = name.lower()
        # Hapus kata "recipes" atau "recipe" agar pencarian lebih luas
        # Misal: "Vegetarian Recipes" -> "Vegetarian"
        remove_terms = ['recipes', 'recipe', 'ideas', 'dishes']
        
        for term in remove_terms:
            clean_name = re.sub(rf'\b{term}\b', '', clean_name)
        
        # Hapus karakter non-alphanumeric
        return ' '.join(re.sub(r'[^\w\s]', '', clean_name).split())

    def _execute_query(self, query):
        try:
            self.sparql.setQuery(query)
            data = self.sparql.query().convert()
            return data.get('results', {}).get('bindings', [])
        except Exception as e:
            logger.warning(f"Query warning: {e}")
            return []

    def _search_item_id(self, name: str) -> Dict:
        """
        Langkah 1: SEARCH BROAD & FILTER LOCALLY (Optimized for CATEGORIES)
        """
        
        # Query Ringan (Sama seperti ingredient)
        query = f"""
        SELECT ?item ?itemLabel ?description ?image WHERE {{
          # Gunakan Index Label
          VALUES ?label {{ "{name}"@en }}
          ?item rdfs:label ?label .
          
          # Ambil info
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 5 
        """
        
        candidates = self._execute_query(query)
        
        if not candidates:
            return None

        # --- PERUBAHAN UTAMA DI SINI ---
        # Keyword khusus untuk Kategori / Diet / Masakan
        valid_keywords = [
            'diet', 'nutrition', 'eating', 'lifestyle',   # Untuk Vegetarian, Keto, Vegan
            'cuisine', 'culinary', 'food', 'culture',     # Untuk Italian, Asian, Mexican
            'meal', 'course', 'breakfast', 'lunch',       # Untuk Dinner, Breakfast
            'dinner', 'supper', 'snack', 'dessert',
            'style', 'cooking', 'tradition'
        ]
        
        invalid_keywords = [
            'company', 'business', 'software', 'band', 'album', 'song', 
            'movie', 'book', 'surname', 'given name', 'village', 'city'
        ]

        best_match = None
        
        for cand in candidates:
            desc = cand.get('description', {}).get('value', '').lower()
            
            is_valid = any(kw in desc for kw in valid_keywords)
            is_invalid = any(kw in desc for kw in invalid_keywords)
            has_image = 'image' in cand
            
            # Prioritas 1: Deskripsi cocok dengan keyword kategori
            if is_valid and not is_invalid:
                return self._format_result(cand)
            
            # Prioritas 2: Punya gambar (Backup)
            if has_image and not is_invalid and best_match is None:
                best_match = cand
            
            # Prioritas 3: Backup terakhir
            if not is_invalid and best_match is None:
                best_match = cand
        
        return self._format_result(best_match) if best_match else None

    def _format_result(self, binding):
        return {
            'uri': binding['item']['value'],
            'label': binding['itemLabel']['value'],
            'description': binding.get('description', {}).get('value', '-'),
            'image_url': binding.get('image', {}).get('value', None)
        }

    def _get_item_details(self, uri: str) -> Dict:
        """
        Langkah 2: Adaptive Detail Fetching.
        (Sama persis dengan Ingredient Enricher, karena ini logic universal)
        """
        query = f"""
        SELECT ?propLabel ?valLabel ?val WHERE {{
          <{uri}> ?p ?val .
          ?prop wikibase:directClaim ?p .
          ?prop wikibase:propertyType ?type .
          
          # Filter sampah
          FILTER(?type != wikibase:ExternalId)
          FILTER(?type != wikibase:Url)
          FILTER(?p != wdt:P18 && ?p != wdt:P373 && ?p != wdt:P910 && ?p != wdt:P1343)
          
          ?prop rdfs:label ?propLabel .
          FILTER(LANG(?propLabel) = "en")
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 100
        """
        
        results = self._execute_query(query)
        
        details = {}
        for r in results:
            prop = r['propLabel']['value']
            val = r.get('valLabel', {}).get('value', r['val']['value'])
            
            if val.startswith("http"): continue
            
            if prop not in details:
                details[prop] = set()
            details[prop].add(val)
            
        final_attributes = {}
        for i, (k, v) in enumerate(details.items()):
            if i >= 15: break
            final_attributes[k] = ", ".join(list(v)[:5])
            
        return final_attributes

    def enrich(self, category_name: str) -> Dict:
        clean_name = self.clean_category_name(category_name)
        logger.info(f"⚡ Enriching Category: '{clean_name}'")
        
        # 1. SEARCH
        basic_info = self._search_item_id(clean_name)
        
        result = {
            'category_name': category_name,
            'clean_name': clean_name,
            'found': False,
            'image_url': "https://via.placeholder.com/150?text=No+Image",
            'description': "-",
            'attributes': {}
        }

        if basic_info:
            result['found'] = True
            result['uri'] = basic_info['uri']
            result['label'] = basic_info['label']
            result['description'] = basic_info['description']
            if basic_info['image_url']:
                result['image_url'] = basic_info['image_url']
            
            # 2. GET DETAILS
            logger.info(f"   ...Fetching details for {basic_info['uri']}...")
            details = self._get_item_details(basic_info['uri'])
            result['attributes'] = details
            
            # Ambil Info Parent (Superclass)
            result['type'] = details.get('subclass of', details.get('instance of', 'Category'))
            
            logger.info(f"   ✅ Done. Found {len(details)} attribute types.")
        else:
            logger.info("   ❌ Not found.")

        return result

# --- TESTING ---
if __name__ == "__main__":
    enricher = WikidataCategoryEnricher()
    
    # Contoh Kategori Resep
    test_cats = ["Vegetarian", "Dinner", "Italian", "Dessert", "Gluten-Free"]
    
    print(f"\n{'CATEGORY':<15} | {'FOUND':<5} | {'DESC (Sample)'}")
    print("-" * 80)
    
    for cat in test_cats:
        data = enricher.enrich(cat)
        
        found = "✅" if data['found'] else "❌"
        desc = data['description'][:40] + "..." if len(data['description']) > 40 else data['description']
        
        print(f"{cat:<15} | {found:<5} | {desc}")
        
        if data['found'] and 'subclass of' in data['attributes']:
             print(f"   -> Parent: {data['attributes']['subclass of']}")