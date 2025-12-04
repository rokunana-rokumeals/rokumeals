"""
Wikidata Comprehensive Enricher
================================================================
Strategi: 2-Step Fetching (Search ID -> Get Details).
Mengambil 10-15 Atribut umum (Image, Class, Parts, Nutrients, dll).
Sangat Cepat & Anti-Timeout.
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import logging
import re
from typing import Dict, List

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WikidataEnricher:
    
    def __init__(self):
        self.sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.sparql.setReturnFormat(JSON)
        self.sparql.addCustomHttpHeader("User-Agent", "UniversityProject-KnowledgeGraph/4.0")
        self.sparql.setTimeout(20) # Aman karena query kita efisien

    def clean_ingredient_name(self, ingredient_name: str) -> str:
        """Membersihkan nama bahan."""
        clean_name = ingredient_name.lower()
        remove_terms = [
            'fresh', 'dried', 'chopped', 'sliced', 'diced', 'minced',
            'ground', 'whole', 'raw', 'cooked', 'organic', 'extra',
            'virgin', 'unsalted', 'salted', 'low', 'fat', 'sodium',
            'cup', 'cups', 'tbsp', 'tsp', 'oz', 'lb', 'gram', 'kg',
            'large', 'small', 'medium', 'clove', 'can', 'bottle'
        ]
        for term in remove_terms:
            clean_name = re.sub(rf'\b{term}\b', '', clean_name)
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
        Langkah 1: SEARCH BROAD & FILTER LOCALLY
        Strategi: Ambil kandidat berdasarkan nama, lalu filter pakai Python.
        Jauh lebih cepat daripada memaksa SPARQL melakukan path traversal.
        """
        
        # 1. Query Ringan (Hanya cek Label & Gambar/Deskripsi)
        query = f"""
        SELECT ?item ?itemLabel ?description ?image WHERE {{
          # Gunakan Index Label (Cepat)
          VALUES ?label {{ "{name}"@en }}
          ?item rdfs:label ?label .
          
          # Ambil info (Optional semua agar tidak membatasi)
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "en") }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 5  # Ambil top 5 kandidat (misal: Apple fruit, Apple company, Apple surname...)
        """
        
        candidates = self._execute_query(query)
        
        if not candidates:
            return None

        # 2. CLIENT-SIDE FILTERING (Python Logic)
        # Daftar kata kunci positif (Bahan Makanan/Kimia)
        valid_keywords = [
            'food', 'fruit', 'vegetable', 'plant', 'berry', 'nut', 'meat', 
            'dish', 'cuisine', 'ingredient', 'spice', 'herb', 'sauce', 
            'liquid', 'water', 'compound', 'chemical', 'mineral', 'substance',
            'sweetener', 'dairy', 'cheese', 'bread', 'cereal', 'condiment',
            'snack', 'beverage', 'drink', 'edible', 'crop', 'legume'
        ]
        
        # Daftar kata kunci negatif (Pasti bukan bahan)
        invalid_keywords = [
            'company', 'business', 'corporation', 'enterprise', 'software',
            'band', 'album', 'song', 'music', 'film', 'movie', 
            'village', 'city', 'town', 'river', 'mountain', 
            'surname', 'given name', 'family name', 'human'
        ]

        best_match = None
        
        for cand in candidates:
            desc = cand.get('description', {}).get('value', '').lower()
            label = cand.get('itemLabel', {}).get('value', '')
            
            # Skor Relevansi Sederhana
            is_valid = any(kw in desc for kw in valid_keywords)
            is_invalid = any(kw in desc for kw in invalid_keywords)
            has_image = 'image' in cand
            
            # LOGIKA PEMILIHAN:
            
            # Prioritas 1: Deskripsi mengandung kata kunci makanan/kimia
            if is_valid and not is_invalid:
                return self._format_result(cand)
            
            # Prioritas 2: Punya gambar DAN tidak mengandung kata kunci negatif (untuk jaga-jaga)
            if has_image and not is_invalid and best_match is None:
                best_match = cand
                
            # Prioritas 3: Simpan kandidat pertama yang tidak invalid sebagai cadangan
            if not is_invalid and best_match is None:
                best_match = cand
        
        # Jika tidak ada yang perfect match (Priority 1), kembalikan match terbaik (Priority 2/3)
        return self._format_result(best_match) if best_match else None

    def _format_result(self, binding):
        """Helper untuk format output"""
        return {
            'uri': binding['item']['value'],
            'label': binding['itemLabel']['value'],
            'description': binding.get('description', {}).get('value', '-'),
            'image_url': binding.get('image', {}).get('value', None)
        }

    def _get_item_details(self, uri: str) -> Dict:
        """
        Langkah 2: Adaptive Detail Fetching (Smart Mode).
        Mengambil atribut apa saja yang tersedia secara dinamis.
        Filter: Hapus ID Eksternal & Metadata teknis.
        Limit: Max 15 atribut paling relevan.
        """
        
        query = f"""
        SELECT ?propLabel ?valLabel ?val WHERE {{
          # Bind URI subject
          <{uri}> ?p ?val .
          
          # Dapatkan Meta-data Properti (untuk filter tipe)
          ?prop wikibase:directClaim ?p .       # Link wdt:Pxx -> wd:Pxx
          ?prop wikibase:propertyType ?type .   # Cek tipe properti
          
          # FILTER 1: Buang External ID (seperti Google KG ID, Freebase ID, dll)
          # Ini penting agar info box bersih dari kode-kode aneh
          FILTER(?type != wikibase:ExternalId)
          
          # FILTER 2: Buang URL/Link Website (Url tipe)
          FILTER(?type != wikibase:Url)
          
          # FILTER 3: Blacklist Properti Metadata/Multimedia yg sudah ada/tidak perlu
          # P18 (Image), P373 (Commons), P910 (Topic Cat), P1343 (Source)
          FILTER(?p != wdt:P18 && ?p != wdt:P373 && ?p != wdt:P910 && ?p != wdt:P1343)
          
          # Ambil Label Properti (Inggris)
          ?prop rdfs:label ?propLabel .
          FILTER(LANG(?propLabel) = "en")
          
          # Magic Service untuk Label Value
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 100
        """
        
        results = self._execute_query(query)
        
        details = {}
        for r in results:
            prop = r['propLabel']['value']
            
            # Trik: Ambil label jika ada, jika tidak ambil raw value (untuk angka/tanggal)
            val = r.get('valLabel', {}).get('value', r['val']['value'])
            
            # Skip jika value masih berupa URL (kadang lolos filter)
            if val.startswith("http"): continue
            
            if prop not in details:
                details[prop] = set()
            details[prop].add(val)
            
        # Finishing: Adaptif max 15 atribut
        final_attributes = {}
        for i, (k, v) in enumerate(details.items()):
            if i >= 15: break # Stop setelah 15 atribut (agar UI tidak kepanjangan)
            final_attributes[k] = ", ".join(list(v)[:5]) # Max 5 value per atribut
            
        return final_attributes

    def enrich(self, ingredient_name: str) -> Dict:
        clean_name = self.clean_ingredient_name(ingredient_name)
        logger.info(f"⚡ Enriching: '{clean_name}'")
        
        # 1. SEARCH
        basic_info = self._search_item_id(clean_name)
        
        result = {
            'ingredient_name': ingredient_name,
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
            
            # Flatten some key attributes for easy access
            result['category'] = details.get('subclass of', details.get('instance of', 'Ingredient'))
            
            logger.info(f"   ✅ Done. Found {len(details)} attribute types.")
        else:
            logger.info("   ❌ Not found.")

        return result

# --- TESTING ---
if __name__ == "__main__":
    enricher = WikidataEnricher()
    
    # Test items: Honey (Kaya fitur), Salt (Non-food class), Chicken (Nutrisi)
    test_items = ["honey", "salt", "chicken breast", "apple"]
    
    print(f"\n{'ITEM':<15} | {'FOUND':<5} | {'ATTRS':<5} | {'DETAILS (Sample)'}")
    print("-" * 80)
    
    for ing in test_items:
        data = enricher.enrich(ing)
        
        found = "✅" if data['found'] else "❌"
        num_attrs = len(data.get('attributes', {}))
        
        # Format sample string
        sample = ""
        if data['found']:
            parts = [f"{k}: {v}" for k, v in list(data['attributes'].items())[:3]]
            sample = " | ".join(parts)
            
        print(f"{ing:<15} | {found:<5} | {num_attrs:<5} | {sample[:50]}...")