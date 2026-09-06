#!/usr/bin/env python3
# main_perfect_timing.py - PRODUCTION-GRADE SECURE RAG SYSTEM v5.0
# STRICT TIMING ENFORCEMENT - Python-level filtering (NOT relying on LLM)
# ============================================================================
# TIMING DEFINITIONS (STRICT):
# ============================================================================
# RESTAURANTS:
#   Breakfast  (9:30 AM)  → tags: breakfast, brunch, meals, fullday
#   Lunch      (2:00 PM)  → tags: lunch, brunch, mainmeals, fullday
#   Dinner     (9:00 PM)  → tags: dinner, mainmeals, meals, fullday
#
# ATTRACTIONS:
#   Morning    (10AM-1PM) → tags: morning, all-day, fullday
#   Afternoon  (3PM-6PM)  → tags: afternoon, all-day, fullday
#   Evening    (7:30PM)   → tags: evening, all-day, fullday
#   Night      (9:30PM+)  → tags: night, all-day, fullday
# ============================================================================

import os
import re
import time
import html
import hashlib
import logging
import random
import unicodedata
import sys
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from pathlib import Path

# ============================================================================
# SECURE LOGGING
# ============================================================================

class SecureLogFormatter(logging.Formatter):
    CONTROL_CHARS = re.compile(r'[\r\n\t\x00-\x1F\x7F-\x9F]')
    def format(self, record):
        if isinstance(record.msg, str):
            record.msg = self.CONTROL_CHARS.sub('', str(record.msg))
        return super().format(record)

logging.basicConfig(filename='security.log', level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
handler = logging.FileHandler('security.log', mode='a', encoding='utf-8')
handler.setFormatter(SecureLogFormatter())
logger.addHandler(handler)

# ============================================================================
# ENVIRONMENT
# ============================================================================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "").strip()
INDEX_PATH = os.getenv("INDEX_PATH", "vector_index.faiss").strip()
FAISS_CHECKSUM = os.getenv("FAISS_CHECKSUM", "").strip() or None
MAX_QUERIES_PER_MINUTE = int(os.getenv("MAX_QUERIES_PER_MINUTE", "10"))

print("=" * 70)
print("🔒 PRODUCTION-GRADE SECURE RAG SYSTEM v5.0")
print("=" * 70)
print("✨ STRICT PYTHON-LEVEL TIMING ENFORCEMENT")
print("   🍽️  Breakfast (9:30 AM)  → breakfast / brunch / meals / fullday / all-day")
print("   🍽️  Lunch    (2:00 PM)  → lunch / brunch / mainmeals / fullday / all-day")
print("   🍽️  Dinner   (9:00 PM)  → dinner / mainmeals / meals / fullday / all-day")
print("   📍 Morning   (10AM-1PM) → morning / fullday / all-day")
print("   📍 Afternoon (3PM-6PM)  → afternoon / fullday / all-day")
print("   📍 Evening   (7:30PM)   → evening / fullday / all-day")
print("   📍 Night     (9:30PM+)  → night / fullday / all-day")
print("=" * 70 + "\n")

# ============================================================================
# TIMING RULES - SINGLE SOURCE OF TRUTH
# ============================================================================

# Maps each "slot" to the timing tags that are VALID for that slot.
# This is enforced at the Python level before anything reaches the LLM.
TIMING_RULES: Dict[str, List[str]] = {
    # Restaurant meal slots
    "breakfast": ["breakfast", "brunch", "meals", "fullday", "all-day", "all day"],
    "lunch":     ["lunch", "brunch", "mainmeals", "fullday", "all-day", "all day"],
    "dinner":    ["dinner", "mainmeals", "meals", "fullday", "all-day", "all day"],
    # Attraction time slots
    "morning":   ["morning", "fullday", "all-day", "all day"],
    "afternoon": ["afternoon", "fullday", "all-day", "all day"],
    "evening":   ["evening", "fullday", "all-day", "all day"],
    "night":     ["night", "fullday", "all-day", "all day"],
}

def parse_timing_tags(timing_raw: str) -> List[str]:
    """
    Parse timing field from the dataset into a list of lowercase tags.
    Handles various formats: 'MainMeals', 'Breakfast Dinner', 'all-day', etc.
    """
    if not timing_raw:
        return ["fullday"]

    timing_lower = str(timing_raw).lower().strip()

    # Treat empty / unknown values as fullday
    if timing_lower in ("", "nan", "none", "not specified", "n/a"):
        return ["fullday"]

    # Normalize separators: commas, slashes, pipes → space
    timing_lower = re.sub(r'[,/|]+', ' ', timing_lower)
    # Remove stray punctuation
    timing_lower = re.sub(r'[^\w\s\-]', ' ', timing_lower)

    # Split on whitespace
    raw_tags = timing_lower.split()

    # Known compound tags that should NOT be split
    compound_map = {
        "mainmeals": "mainmeals",
        "allday":    "all-day",
        "all-day":   "all-day",
        "all":       None,  # may appear as part of "all day" split
        "day":       None,  # may appear as part of "all day" split
        "fullday":   "fullday",
    }

    tags = set()
    i = 0
    while i < len(raw_tags):
        token = raw_tags[i]

        # Handle "all day" written as two tokens
        if token == "all" and i + 1 < len(raw_tags) and raw_tags[i + 1] == "day":
            tags.add("all-day")
            i += 2
            continue

        if token in compound_map:
            resolved = compound_map[token]
            if resolved:
                tags.add(resolved)
        else:
            tags.add(token)

        i += 1

    return list(tags) if tags else ["fullday"]


def place_matches_slot(timing_raw: str, slot: str) -> bool:
    """
    Strictly check whether a place's timing field matches the required slot.

    Args:
        timing_raw: Raw timing string from the dataset (e.g. "MainMeals", "Breakfast Dinner")
        slot: One of: breakfast, lunch, dinner, morning, afternoon, evening, night

    Returns:
        True only if at least one of the place's timing tags is valid for the slot.
    """
    slot = slot.lower()
    valid_tags = TIMING_RULES.get(slot, [])
    if not valid_tags:
        # Unknown slot — don't filter (safe fallback)
        return True

    place_tags = parse_timing_tags(timing_raw)

    for tag in place_tags:
        if tag in valid_tags:
            return True

    return False  # ← Strict: place does NOT match this slot


def timing_display(timing_raw: str) -> str:
    """Return a clean, human-readable timing label."""
    tags = parse_timing_tags(timing_raw)
    return " / ".join(t.capitalize() for t in sorted(tags))

# ============================================================================
# API KEY VALIDATION
# ============================================================================

def validate_api_key(key: str) -> str:
    if not key:
        raise ValueError("GROQ_API_KEY missing in .env file")
    key = key.strip()
    if len(key) < 20 or len(key) > 200:
        raise ValueError(f"Invalid API key length: {len(key)}")
    if not re.match(r'^[a-zA-Z0-9\-_]+$', key):
        raise ValueError("Invalid API key format")
    return key

try:
    API_KEY = validate_api_key(API_KEY)
except ValueError as e:
    logger.critical(f"API key validation failed: {e}")
    print(f"❌ ERROR: {e}")
    sys.exit(1)

# ============================================================================
# PATH VALIDATION
# ============================================================================

def validate_safe_path(filepath: str, allowed_dir: str = ".") -> str:
    try:
        if not filepath or len(filepath) > 4096:
            raise ValueError("Invalid filepath")
        filepath = unicodedata.normalize('NFKC', filepath)
        if '\x00' in filepath:
            raise ValueError("NULL byte injection detected")
        path = Path(filepath).resolve(strict=False)
        allowed = Path(allowed_dir).resolve(strict=False)
        try:
            path.relative_to(allowed)
        except ValueError:
            raise ValueError(f"Path traversal blocked: {filepath}")
        if path.is_symlink():
            target = path.readlink().resolve(strict=False)
            try:
                target.relative_to(allowed)
            except ValueError:
                raise ValueError("Symlink escape blocked")
        return str(path)
    except Exception as e:
        logger.error(f"Path validation failed: {e}")
        raise ValueError(f"Invalid path: {filepath}")

INDEX_PATH = validate_safe_path(INDEX_PATH, ".")

if not os.path.exists(INDEX_PATH):
    print(f"❌ ERROR: FAISS index not found. Run: python encoding_secure_faiss.py")
    sys.exit(1)

# ============================================================================
# FAISS INTEGRITY
# ============================================================================

def verify_faiss_integrity(index_path: str, expected_checksum: str) -> bool:
    index_file = os.path.join(index_path, "index.faiss") if os.path.isdir(index_path) else index_path
    if not os.path.exists(index_file):
        return False
    hasher = hashlib.sha256()
    with open(index_file, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest() == expected_checksum

if FAISS_CHECKSUM:
    print("🔐 Verifying FAISS index integrity...")
    if verify_faiss_integrity(INDEX_PATH, FAISS_CHECKSUM):
        print("   ✅ Integrity check PASSED\n")
    else:
        print("❌ CRITICAL: Index integrity verification FAILED")
        sys.exit(1)
else:
    print("⚠️  FAISS integrity check SKIPPED (checksum not configured)\n")

# ============================================================================
# LOAD MODELS
# ============================================================================

print("⏳ Loading models...")
try:
    embedding_model = HuggingFaceEmbeddings(
        model_name="thenlper/gte-small",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    vector_store = FAISS.load_local(
        INDEX_PATH, embedding_model, allow_dangerous_deserialization=True
    )
    index_size = vector_store.index.ntotal if hasattr(vector_store, 'index') else 0
    print(f"   ✅ Vector store loaded ({index_size:,} vectors)")

    llm_model = ChatGroq(
        api_key=API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=4096,
        timeout=30
    )
    masked_key = API_KEY[:4] + "*" * (len(API_KEY) - 8) + API_KEY[-4:]
    print(f"   ✅ LLM loaded ({masked_key})\n")
except Exception as e:
    print(f"❌ ERROR: Failed to load models: {type(e).__name__}: {str(e)}")
    sys.exit(1)

# ============================================================================
# DYNAMIC CITY LOADING
# ============================================================================

def load_cities_from_dataset() -> List[str]:
    try:
        cities = set()
        for query in ["Pakistan", "city", "places", "travel"]:
            try:
                docs = vector_store.similarity_search(query, k=200)
                for doc in docs:
                    city = doc.metadata.get('Places_city', '').strip()
                    if city and len(city) > 2:
                        cities.add(city.lower())
            except Exception:
                continue
        if cities:
            city_list = sorted(list(cities))
            print(f"✅ Loaded {len(city_list)} cities from dataset\n")
            return city_list
    except Exception as e:
        logging.warning(f"Could not load cities: {e}")
    fallback = ["karachi", "lahore", "islamabad", "rawalpindi", "faisalabad",
                "multan", "peshawar", "quetta", "hyderabad", "abbottabad"]
    print(f"⚠️  Using fallback city list\n")
    return fallback

PAKISTAN_CITIES = load_cities_from_dataset()
CITY_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(c) for c in PAKISTAN_CITIES) + r')\b',
    re.IGNORECASE
)

# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    def __init__(self, rate: int = 10, per: int = 60):
        self.rate = rate; self.per = per
        self.allowance = rate; self.last_check = time.time()
    def allow_request(self) -> bool:
        current = time.time()
        self.allowance += (current - self.last_check) * (self.rate / self.per)
        self.last_check = current
        if self.allowance > self.rate: self.allowance = self.rate
        if self.allowance < 1.0: return False
        self.allowance -= 1.0; return True

rate_limiter = RateLimiter(rate=MAX_QUERIES_PER_MINUTE, per=60)

# ============================================================================
# INPUT SANITIZATION
# ============================================================================

def sanitize_user_input(user_input: str, max_length: int = 500) -> str:
    if not user_input: return ""
    if len(user_input) > max_length:
        raise ValueError(f"Input too long (max {max_length} chars)")
    user_input = unicodedata.normalize('NFKC', user_input)
    user_input = ''.join(c for c in user_input
                         if unicodedata.category(c)[0] not in ('C',) or c in (' ', '\n'))
    user_input = html.escape(user_input, quote=True)
    dangerous_patterns = [
        r'(?i)(<|&lt;)script', r'(?i)javascript:', r'(?i)on\w+\s*=',
        r'(?i)(eval|exec|__import__|compile)\s*[\(\[]',
        r'(?i)(DROP|DELETE|INSERT|UPDATE|SELECT)\s+',
        r'[\|\&\;]\s*(sh|bash|cmd|powershell)',
        r'(?i)(&&|\|\|).*?(rm|del|format)',
        r'\$\{.*?\}', r'\{\{.*?\}\}', r'<%.*?%>', r'%0[ad]',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, user_input):
            raise ValueError("Potentially malicious content detected")
    if not re.match(r'^[a-zA-Z0-9\s\.,\-\?\!\'\"]+$', user_input):
        raise ValueError("Invalid characters in input")
    return user_input.strip()

def detect_prompt_injection(query: str) -> bool:
    patterns = [
        r'(?i)ignore\s+(all\s+)?previous\s+instructions',
        r'(?i)you\s+are\s+now', r'(?i)forget\s+(everything|all)',
        r'(?i)new\s+(role|instructions|system)', r'(?i)system\s+prompt',
        r'(?i)reveal\s+your', r'(?i)act\s+as\s+a\s+(?!travel)',
        r'(?i)roleplay', r'(?i)pretend\s+(to\s+be|you\s+are)',
    ]
    for p in patterns:
        if re.search(p, query): return True
    return False

# ============================================================================
# QUERY PARSING
# ============================================================================

def extract_cities_from_query(query: str) -> List[str]:
    matches = CITY_PATTERN.findall(query.lower())
    return [m.title() for m in matches]

def parse_travel_intent(query: str) -> Dict[str, Any]:
    query_lower = query.lower()
    cities = extract_cities_from_query(query)
    destination_city = None
    from_to = re.search(r'from\s+(\w+(?:\s+\w+)?)\s+to\s+(\w+(?:\s+\w+)?)', query_lower)
    if from_to:
        potential_dest = from_to.group(2).strip()
        for city in PAKISTAN_CITIES:
            if potential_dest in city or city in potential_dest:
                destination_city = city.title(); break
        if not destination_city and len(cities) >= 2:
            destination_city = cities[-1]
    elif cities:
        destination_city = cities[-1] if any(
            w in query_lower for w in [" in ", "visit", "explore", "trip to", "travel to"]
        ) else cities[0]
    duration_match = re.search(r'(\d+)\s*(?:day|days)', query_lower)
    duration = min(max(int(duration_match.group(1)) if duration_match else 3, 1), 14)
    budget_pref = None
    if any(t in query_lower for t in ["moderate", "mid", "medium", "average"]):
        budget_pref = "moderate"
    elif any(t in query_lower for t in ["low budget", "cheap", "budget", "affordable"]):
        budget_pref = "low"
    elif any(t in query_lower for t in ["luxury", "expensive", "high budget", "premium"]):
        budget_pref = "high"
    return {
        "destination_city": destination_city,
        "all_cities": cities,
        "duration": duration,
        "budget_preference": budget_pref,
        "query": query
    }

# ============================================================================
# PLACE CATEGORIZATION + BUDGET
# ============================================================================

def categorize_place_type(place_type: str) -> str:
    t = place_type.lower()
    if any(k in t for k in ["hotel", "motel", "lodge", "inn", "resort", "guest house"]):
        return "hotel"
    if any(k in t for k in ["restaurant", "cafe", "coffee", "food", "eatery", "dining",
                              "bakery", "pizza", "burger", "grill", "diner"]):
        return "restaurant"
    return "attraction"

def normalize_budget_category(budget_str: str) -> str:
    if not budget_str or budget_str.lower() in ["not specified", "nan", "none"]:
        return "unspecified"
    budget_lower = budget_str.lower()
    numbers = re.findall(r'\d+', budget_str)
    if numbers:
        avg = sum(int(n) for n in numbers) / len(numbers)
        if avg < 500: return "low"
        elif avg < 2000: return "moderate"
        else: return "high"
    if any(t in budget_lower for t in ["low", "cheap", "budget", "affordable"]):
        return "low"
    elif any(t in budget_lower for t in ["moderate", "mid", "medium", "average"]):
        return "moderate"
    elif any(t in budget_lower for t in ["high", "luxury", "expensive", "premium"]):
        return "high"
    return "unspecified"

def get_budget_emoji(cat: str) -> str:
    return {"low": "💵", "moderate": "💳", "high": "💎"}.get(cat.lower(), "💰")

# ============================================================================
# PLACE NAME NORMALIZATION
# ============================================================================

def normalize_place_name(name: str) -> str:
    normalized = re.sub(r'[^\w\s]', '', name.lower())
    normalized = ' '.join(normalized.split())
    stop_words = {'the', 'a', 'an', 'and', 'or', 'of', 'at', 'in'}
    return ' '.join(w for w in normalized.split() if w not in stop_words)

# ============================================================================
# STRICT TIMING-BASED RESTAURANT POOLS
# ============================================================================

def build_restaurant_pools(restaurants: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Pre-build three restaurant pools (breakfast / lunch / dinner) using
    STRICT Python-level timing filtering.  Each pool contains ONLY places
    whose dataset timing tag is valid for that meal.
    """
    pools: Dict[str, List[Dict]] = {"breakfast": [], "lunch": [], "dinner": []}
    for r in restaurants:
        timing_raw = r.get("timing_raw", "")
        for meal in ("breakfast", "lunch", "dinner"):
            if place_matches_slot(timing_raw, meal):
                pools[meal].append(r)
    return pools

def build_attraction_pools(attractions: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Pre-build four attraction pools using STRICT Python-level timing filtering.
    """
    pools: Dict[str, List[Dict]] = {
        "morning": [], "afternoon": [], "evening": [], "night": []
    }
    for a in attractions:
        timing_raw = a.get("timing_raw", "")
        for slot in ("morning", "afternoon", "evening", "night"):
            if place_matches_slot(timing_raw, slot):
                pools[slot].append(a)
    return pools

# ============================================================================
# RETRIEVAL WITH STRICT FILTERING
# ============================================================================

def retrieve_and_filter_places(
    intent: Dict[str, Any],
    k_per_query: int = 150
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Retrieve places and apply STRICT timing + city + budget filters."""

    MAX_DOCS = 600
    destination_city = intent.get("destination_city")
    budget_pref = intent.get("budget_preference")

    # Build search queries
    queries = []
    if destination_city:
        queries += [
            destination_city,
            f"places to visit in {destination_city}",
            f"{destination_city} attractions",
            f"restaurants in {destination_city}",
            f"hotels in {destination_city}",
        ]
    else:
        queries += ["Pakistan travel places", "tourist attractions Pakistan"]
    queries.append(intent["query"])

    all_docs = []
    seen_ids = set()
    seen_norm = set()

    print(f"🔍 Searching database for {destination_city or 'Pakistan'}...")

    for query in queries[:8]:
        if len(all_docs) >= MAX_DOCS:
            break
        try:
            docs = vector_store.similarity_search(query, k=min(k_per_query, MAX_DOCS - len(all_docs)))
            for doc in docs:
                name = doc.metadata.get('Places_name', '').strip()
                norm = normalize_place_name(name)
                doc_id = f"{name}_{doc.metadata.get('Places_city')}"
                if doc_id not in seen_ids and norm not in seen_norm:
                    all_docs.append(doc)
                    seen_ids.add(doc_id)
                    seen_norm.add(norm)
        except Exception as e:
            logger.warning(f"Search failed: {e}")

    print(f"   Raw results: {len(all_docs)} unique places")

    hotels, restaurants, attractions = [], [], []
    seen_final = set()

    for doc in all_docs:
        meta = doc.metadata
        name       = meta.get('Places_name', '').strip()
        place_type = meta.get('Places_type', '').strip()
        city       = meta.get('Places_city', '').strip()
        ref        = meta.get('Places_reference', '').strip()
        budget_raw = meta.get('Budget', 'Not specified')
        timing_raw = meta.get('timing', '')  # ← Raw timing from dataset

        if not name or not city:
            continue

        norm = normalize_place_name(name)
        if norm in seen_final:
            continue

        # ── City filter ──────────────────────────────────────────────────────
        if destination_city and city.lower().strip() != destination_city.lower().strip():
            continue

        # ── Budget filter ────────────────────────────────────────────────────
        budget_cat = normalize_budget_category(budget_raw)
        if budget_pref and budget_cat != "unspecified":
            order = {"low": 0, "moderate": 1, "high": 2}
            mapped = "moderate" if budget_pref == "medium" else budget_pref
            if mapped in order and budget_cat in order:
                if abs(order[mapped] - order[budget_cat]) > 1:
                    continue

        seen_final.add(norm)

        entry = {
            'name':           name,
            'type':           place_type,
            'city':           city,
            'link':           ref if ref else
                              f"https://www.google.com/maps/search/"
                              f"{name.replace(' ', '+')}+{city.replace(' ', '+')}",
            'budget':         budget_raw,
            'budget_category': budget_cat,
            'timing_raw':     timing_raw,                    # ← Keep raw for filtering
            'timing_display': timing_display(timing_raw),    # ← Pretty label
        }

        cat = categorize_place_type(place_type)
        if cat == "hotel":
            hotels.append(entry)
        elif cat == "restaurant":
            restaurants.append(entry)
        else:
            attractions.append(entry)

    random.shuffle(hotels)
    random.shuffle(restaurants)
    random.shuffle(attractions)

    # ── Build strict timing pools ────────────────────────────────────────────
    r_pools = build_restaurant_pools(restaurants)
    a_pools = build_attraction_pools(attractions)

    print(f"   Filtered totals: {len(hotels)} hotels | "
          f"{len(restaurants)} restaurants | {len(attractions)} attractions")
    print(f"\n   📊 STRICT TIMING POOLS:")
    print(f"   ──────────────────────────────────────────")
    print(f"   🍽️  Restaurants:")
    print(f"      • Breakfast-valid : {len(r_pools['breakfast'])}")
    print(f"      • Lunch-valid     : {len(r_pools['lunch'])}")
    print(f"      • Dinner-valid    : {len(r_pools['dinner'])}")
    print(f"   📍 Attractions:")
    print(f"      • Morning-valid   : {len(a_pools['morning'])}")
    print(f"      • Afternoon-valid : {len(a_pools['afternoon'])}")
    print(f"      • Evening-valid   : {len(a_pools['evening'])}")
    print(f"      • Night-valid     : {len(a_pools['night'])}")
    print(f"   ──────────────────────────────────────────\n")

    return hotels, restaurants, attractions, r_pools, a_pools

# ============================================================================
# CONTEXT BUILDER - PRE-SORTED BY SLOT
# ============================================================================

def format_context(
    intent: Dict[str, Any],
    hotels: List[Dict],
    restaurants: List[Dict],
    attractions: List[Dict],
    r_pools: Dict[str, List[Dict]],
    a_pools: Dict[str, List[Dict]],
) -> str:
    """
    Format context for the LLM.  Each section is already filtered to the
    correct timing pool so the LLM cannot pick a wrong-timing restaurant.
    """
    destination = intent.get("destination_city") or "Pakistan"
    budget      = intent.get("budget_preference") or "Any"
    duration    = intent.get("duration", 3)

    def fmt_place(prefix: str, idx: int, p: Dict) -> str:
        emoji = get_budget_emoji(p['budget_category'])
        return (f"{prefix}{idx}. {p['name']} | {p['type']} | {p['link']} | "
                f"({emoji} {p['budget_category'].upper()}) | ⏰ {p['timing_display']} ⏰\n")

    ctx  = f"=== {destination.upper()} TRAVEL DATA ===\n"
    ctx += f"Duration: {duration} days | Budget: {budget.title()}\n\n"

    # Hotels
    ctx += "🏨 HOTELS (pick exactly ONE - used for check-in Day1 & check-out last day):\n"
    for i, h in enumerate(hotels[:8], 1):
        ctx += fmt_place("H", i, h)
    ctx += "\n"

    # Restaurant pools - STRICTLY filtered
    ctx += "🍳 BREAKFAST RESTAURANTS (valid ONLY at 9:30 AM):\n"
    bfast = r_pools["breakfast"]
    if bfast:
        for i, r in enumerate(bfast[:duration * 3], 1):
            ctx += fmt_place("B", i, r)
    else:
        ctx += "  ⚠️  NONE AVAILABLE - use FREE TIME slot instead\n"
    ctx += "\n"

    ctx += "🍽️ LUNCH RESTAURANTS (valid ONLY at 2:00 PM):\n"
    lunch = r_pools["lunch"]
    if lunch:
        for i, r in enumerate(lunch[:duration * 3], 1):
            ctx += fmt_place("L", i, r)
    else:
        ctx += "  ⚠️  NONE AVAILABLE - use FREE TIME slot instead\n"
    ctx += "\n"

    ctx += "🍷 DINNER RESTAURANTS (valid ONLY at 9:00 PM):\n"
    dinner = r_pools["dinner"]
    if dinner:
        for i, r in enumerate(dinner[:duration * 3], 1):
            ctx += fmt_place("D", i, r)
    else:
        ctx += "  ⚠️  NONE AVAILABLE - use FREE TIME slot instead\n"
    ctx += "\n"

    # Attraction pools - STRICTLY filtered
    for slot, label, note in [
        ("morning",   "🌅 MORNING ATTRACTIONS   (10:00 AM – 1:00 PM)", "Morning/Fullday/All-day"),
        ("afternoon", "☀️  AFTERNOON ATTRACTIONS (3:00 PM – 6:00 PM)", "Afternoon/Fullday/All-day"),
        ("evening",   "🌆 EVENING ATTRACTIONS   (7:30 PM)",            "Evening/Fullday/All-day"),
        ("night",     "🌙 NIGHT ATTRACTIONS     (9:30 PM+)",           "Night/Fullday/All-day"),
    ]:
        ctx += f"{label} — tags: {note}\n"
        pool = a_pools[slot]
        if pool:
            for i, a in enumerate(pool[:duration * 6], 1):
                ctx += fmt_place(slot[0].upper(), i, a)
        else:
            ctx += "  ⚠️  NONE AVAILABLE - use FREE TIME slot instead\n"
        ctx += "\n"

    ctx += "=" * 70 + "\n"
    ctx += "🚨 ABSOLUTE RULES:\n"
    ctx += "1. ONLY use places listed in the section matching the time slot above.\n"
    ctx += "   • Breakfast time → ONLY from 🍳 BREAKFAST section\n"
    ctx += "   • Lunch time     → ONLY from 🍽️ LUNCH section\n"
    ctx += "   • Dinner time    → ONLY from 🍷 DINNER section\n"
    ctx += "   • Morning slot   → ONLY from 🌅 MORNING ATTRACTIONS section\n"
    ctx += "   • Afternoon slot → ONLY from ☀️  AFTERNOON ATTRACTIONS section\n"
    ctx += "   • Evening slot   → ONLY from 🌆 EVENING ATTRACTIONS section\n"
    ctx += "   • Night slot     → ONLY from 🌙 NIGHT ATTRACTIONS section\n"
    ctx += "2. If a section is empty → use FREE TIME (🕐 FREE TIME: Relax, explore)\n"
    ctx += "3. NEVER use a place from the wrong section\n"
    ctx += "4. NEVER reuse any place (except hotel: check-in + check-out only)\n"
    ctx += "5. NEVER invent places not listed above\n"
    ctx += "=" * 70 + "\n\n"

    return ctx

# ============================================================================
# PROMPT TEMPLATE
# ============================================================================

PROMPT_TEMPLATE = """You are a Pakistan Travel Itinerary AI. Generate a {duration}-day itinerary.

<ABSOLUTE_TIMING_RULES>
Each time slot has its OWN section in the data below. You MUST use ONLY places
from the matching section. Never cross-use sections.

  9:30 AM  Breakfast → use ONLY 🍳 BREAKFAST RESTAURANTS
  2:00 PM  Lunch     → use ONLY 🍽️ LUNCH RESTAURANTS  
  9:00 PM  Dinner    → use ONLY 🍷 DINNER RESTAURANTS
  10AM-1PM Morning   → use ONLY 🌅 MORNING ATTRACTIONS
  3PM-6PM  Afternoon → use ONLY ☀️  AFTERNOON ATTRACTIONS
  7:30 PM  Evening   → use ONLY 🌆 EVENING ATTRACTIONS
  9:30 PM+ Night     → use ONLY 🌙 NIGHT ATTRACTIONS

If a section is empty → write: **TIME** – 🕐 FREE TIME: Relax or explore
</ABSOLUTE_TIMING_RULES>

<DAILY_STRUCTURE>
Day 1:
  9:00 AM   🏨 Check-in at hotel
  9:30 AM   🍳 Breakfast (from BREAKFAST section)
  10:00 AM  📍 Morning attraction 1 (from MORNING section)
  11:00 AM  📍 Morning attraction 2 (from MORNING section)
  12:00 PM  📍 Morning attraction 3 (from MORNING section)
  1:00 PM   📍 Morning attraction 4 (from MORNING section)
  2:00 PM   🍽️ Lunch (from LUNCH section)
  3:00 PM   📍 Afternoon attraction 1 (from AFTERNOON section)
  4:00 PM   📍 Afternoon attraction 2 (from AFTERNOON section)
  5:00 PM   📍 Afternoon attraction 3 (from AFTERNOON section)
  6:00 PM   📍 Afternoon attraction 4 (from AFTERNOON section)
  7:30 PM   📍 Evening attraction (from EVENING section)
  9:00 PM   🍷 Dinner (from DINNER section)
  9:30 PM   📍 Night attraction (from NIGHT section) [if available]
  10:30 PM  🏨 Rest at hotel

Middle days: same structure, no check-in
Last day: Breakfast → 2-3 Morning → Lunch → 1-2 Afternoon → 6:00 PM Check-out → Depart
</DAILY_STRUCTURE>

<OUTPUT_FORMAT>
- Headers: ### Day 1, ### Day 2 ...
- Numbered lists: 1. 2. 3.
- Bold times: **9:00 AM**
- Place format: **TIME** – EMOJI Activity at [Name](link) - Type (EMOJI BUDGET) ⏰ Timing ⏰
- Hotel check-in:  **9:00 AM** – 🏨 Check-in at [Hotel](link) - Hotel (💵 LOW) ⏰ Fullday ⏰
- Hotel check-out: **6:00 PM** – 🏨 Check-out from [Hotel](link) - Hotel (💵 LOW) ⏰ Fullday ⏰
- Departure: **6:30 PM** – 🚗 Departure
- FREE TIME: **TIME** – 🕐 FREE TIME: Relax, explore, or rest
- No "wake up" messages, no day subtitles
</OUTPUT_FORMAT>

DATA:
{context}

USER QUERY: {question}

Generate the {duration}-day itinerary now. Follow timing rules STRICTLY."""

# ============================================================================
# QUALITY ANALYSIS
# ============================================================================

def analyze_itinerary(content: str, intent: Dict[str, Any]) -> Dict[str, Any]:
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    links = re.findall(link_pattern, content)
    place_names = [l[0] for l in links]
    days_covered = len(set(re.findall(r'### Day (\d+)', content)))
    duration = intent.get('duration', 3)
    place_counts = Counter(place_names)
    checkin  = set(re.findall(r'Check-in at \[([^\]]+)\]', content))
    checkout = set(re.findall(r'Check-out from \[([^\]]+)\]', content))
    valid_hotel_pairs = checkin & checkout
    duplicates = {n: c for n, c in place_counts.items()
                  if c > 1 and n not in valid_hotel_pairs}
    breakfast_count = content.count('🍳 Breakfast') + content.count('🍽️ Breakfast')
    lunch_count     = content.count('🍽️ Lunch')
    dinner_count    = content.count('🍷 Dinner')
    free_time_count = content.count('🕐 FREE TIME')
    total_meals     = breakfast_count + lunch_count + dinner_count
    score = 0
    score += min(25, (len(links) / (duration * 10)) * 25)
    score += (days_covered / duration) * 20 if duration else 0
    score += min(20, (total_meals / (duration * 3)) * 20) if duration else 0
    score += 20 if not duplicates else max(0, 20 - len(duplicates) * 4)
    score += 10 if valid_hotel_pairs else 0
    score += 5  if content.count('⏰') >= len(links) else 0
    return {
        'clickable_links':   len(links),
        'days_covered':      days_covered,
        'expected_days':     duration,
        'unique_places':     len(set(place_names)) - len(valid_hotel_pairs),
        'duplicates':        duplicates,
        'duplicate_count':   len(duplicates),
        'valid_hotel_pairs': valid_hotel_pairs,
        'breakfast_count':   breakfast_count,
        'lunch_count':       lunch_count,
        'dinner_count':      dinner_count,
        'total_meals':       total_meals,
        'expected_meals':    duration * 3,
        'free_time_slots':   free_time_count,
        'quality_score':     min(100, int(score)),
        'duration':          duration,
    }

def print_quality_report(analysis: Dict[str, Any]):
    print("\n" + "=" * 70)
    print("📊 ITINERARY QUALITY REPORT - STRICT TIMING v5.0")
    print("=" * 70)
    if analysis.get('valid_hotel_pairs'):
        print("\n🏨 HOTEL:")
        for h in analysis['valid_hotel_pairs']:
            print(f"   ✅ '{h}' — Check-in Day 1, Check-out Last Day")
    if analysis['duplicate_count'] > 0:
        print(f"\n🚨 DUPLICATES DETECTED: {analysis['duplicate_count']}")
        for name, count in analysis['duplicates'].items():
            print(f"   ❌ '{name}' used {count} times")
    else:
        print(f"\n✅ DUPLICATE CHECK: PASSED ({analysis['unique_places']} unique places)")
    print(f"\n📈 QUALITY METRICS:")
    print(f"   • Clickable links  : {analysis['clickable_links']}")
    print(f"   • Days covered     : {analysis['days_covered']}/{analysis['expected_days']}")
    print(f"   • Meals            : {analysis['total_meals']}/{analysis['expected_meals']}")
    print(f"   • Free time slots  : {analysis['free_time_slots']}")
    print(f"   • Quality score    : {analysis['quality_score']}/100")
    print("=" * 70 + "\n")

# ============================================================================
# MAIN CHAT LOOP
# ============================================================================

def main():
    print("Welcome to Pakistan Travel Itinerary Chat - STRICT TIMING v5.0!")
    print("=" * 70)
    print("Timing is enforced at the Python level before the LLM sees any data.")
    print("Each meal/visit slot shows ONLY places valid for that time.\n")
    print("Examples:")
    print("  • Plan a 3 day trip to Karachi with low budget")
    print("  • Create a 4 days itinerary from Lahore to Islamabad")
    print("\nType 'exit' to quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() == "exit":
                print("👋 Goodbye!")
                break
            if not rate_limiter.allow_request():
                print("⏳ Rate limit exceeded. Please wait 60 seconds...\n")
                time.sleep(5)
                continue
            try:
                if len(user_input) > 500:
                    print("❌ Query too long (max 500 characters)\n"); continue
                sanitized = sanitize_user_input(user_input)
                if detect_prompt_injection(sanitized):
                    print("⚠️  Query contains disallowed instructions.\n"); continue
            except ValueError as e:
                print(f"❌ Invalid input: {e}\n"); continue

            print("\n⏳ Analyzing request...")
            intent = parse_travel_intent(sanitized)
            print(f"   📍 Destination : {intent['destination_city'] or 'Not specified'}")
            print(f"   📅 Duration    : {intent['duration']} days")
            print(f"   💰 Budget      : {intent['budget_preference'] or 'Any'}\n")

            # Retrieval now returns strict timing pools too
            result = retrieve_and_filter_places(intent)
            hotels, restaurants, attractions, r_pools, a_pools = result

            if not hotels:
                print("⚠️  No hotels found for this destination!\n"); continue

            context = format_context(intent, hotels, restaurants, attractions, r_pools, a_pools)

            if len(context) > 12000:
                context = '\n'.join(context.split('\n')[:350])

            prompt = PROMPT_TEMPLATE.format(
                context=context,
                question=sanitized,
                duration=intent['duration']
            )

            print("🤖 Generating itinerary with STRICT TIMING enforcement...\n")

            response = None
            for attempt in range(3):
                try:
                    response = llm_model.invoke(prompt)
                    break
                except Exception as api_err:
                    err_type = type(api_err).__name__
                    if any(t in err_type for t in ["APIConnection", "Connection", "Timeout"]):
                        if attempt < 2:
                            wait = [5, 10, 20][attempt]
                            print(f"⚠️  {err_type} — Retry {attempt+1}/2 in {wait}s...")
                            time.sleep(wait)
                        else:
                            print("❌ API connection failed after 3 attempts.\n")
                            response = None
                    else:
                        raise

            if response is None:
                continue

            content = response.content
            print("=" * 70)
            print("✈️  YOUR ITINERARY - STRICT TIMING v5.0")
            print("=" * 70)
            print(content)
            print("=" * 70)

            analysis = analyze_itinerary(content, intent)
            print_quality_report(analysis)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"❌ An error occurred: {type(e).__name__}: {str(e)}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {type(e).__name__}")
        sys.exit(1)