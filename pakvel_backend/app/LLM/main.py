#!/usr/bin/env python3
# main.py - PRODUCTION-GRADE SECURE RAG SYSTEM v4.1
# ============================================================================
# FIXES:
# 1. APIStatusError handled with status-code-aware retry logic
# 2. Rate-limit (429) → wait and retry
# 3. Auth errors (401/403) → clear message, no retry
# 4. Server errors (500/502/503) → retry with backoff
# 5. All other APIStatusError subtypes → logged and shown clearly
# ============================================================================

import os, re, time, html, hashlib, logging, random, unicodedata, sys
from typing import List, Dict, Tuple, Set, Any
from collections import Counter
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from pathlib import Path

# Try to import groq for specific error handling
try:
    from groq import APIStatusError as GroqAPIStatusError
    from groq import RateLimitError, AuthenticationError, APIConnectionError
    GROQ_ERRORS_AVAILABLE = True
except ImportError:
    GROQ_ERRORS_AVAILABLE = False

# ── Logging ───────────────────────────────────────────────────────────────────
class SecureLogFormatter(logging.Formatter):
    CTRL = re.compile(r"[\r\n\t\x00-\x1F\x7F-\x9F]")
    def format(self, record):
        if isinstance(record.msg, str):
            record.msg = self.CTRL.sub("", str(record.msg))
        return super().format(record)

logging.basicConfig(filename="security.log", level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)
_h = logging.FileHandler("security.log", mode="a", encoding="utf-8")
_h.setFormatter(SecureLogFormatter())
logger.addHandler(_h)

load_dotenv()
API_KEY             = os.getenv("GROQ_API_KEY", "").strip()
BASE_DIR = os.path.dirname(__file__)
INDEX_PATH = os.path.join(BASE_DIR, os.getenv("INDEX_PATH", "vector_index.faiss").strip())
FAISS_CHECKSUM      = os.getenv("FAISS_CHECKSUM", "").strip() or None
MAX_QUERIES_PER_MIN = int(os.getenv("MAX_QUERIES_PER_MINUTE", "10"))

print("=" * 70)
print("PAKISTAN TRAVEL RAG v4.1")
print("=" * 70)

# ── API Key ───────────────────────────────────────────────────────────────────
def validate_api_key(key):
    if not key: raise ValueError("GROQ_API_KEY missing")
    key = key.strip()
    if not (20 <= len(key) <= 200): raise ValueError(f"Bad key length {len(key)}")
    if not re.match(r"^[a-zA-Z0-9\-_]+$", key): raise ValueError("Bad key chars")
    return key

try:
    API_KEY = validate_api_key(API_KEY)
except ValueError as e:
    print(f"ERROR: {e}"); sys.exit(1)

# ── Path Validation ───────────────────────────────────────────────────────────
def validate_safe_path(fp, allowed="."):
    try:
        if not fp or len(fp) > 4096: raise ValueError("Invalid filepath")
        fp = unicodedata.normalize("NFKC", fp)
        if "\x00" in fp: raise ValueError("NULL byte")
        p = Path(fp).resolve(strict=False)
        a = Path(allowed).resolve(strict=False)
        try: p.relative_to(a)
        except ValueError: raise ValueError(f"Path traversal: {fp}")
        if p.is_symlink():
            t = p.readlink().resolve(strict=False)
            try: t.relative_to(a)
            except ValueError: raise ValueError("Symlink escape")
        return str(p)
    except Exception as e: raise ValueError(f"Invalid path: {e}")

INDEX_PATH = validate_safe_path(INDEX_PATH, BASE_DIR)
if not os.path.exists(INDEX_PATH):
    print("ERROR: FAISS index not found. Run: python encoding_rebuild.py"); sys.exit(1)

# ── FAISS Integrity ───────────────────────────────────────────────────────────
if FAISS_CHECKSUM:
    f = os.path.join(INDEX_PATH, "index.faiss") if os.path.isdir(INDEX_PATH) else INDEX_PATH
    h = hashlib.sha256(open(f,"rb").read()).hexdigest()
    if h != FAISS_CHECKSUM: print("CRITICAL: FAISS integrity FAILED"); sys.exit(1)
    print("FAISS integrity OK\n")
else:
    print("WARNING: FAISS integrity check SKIPPED\n")

# ── Load Models ───────────────────────────────────────────────────────────────
print("Loading models...")
try:
    embedding_model = HuggingFaceEmbeddings(
        model_name="thenlper/gte-small",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    vector_store = FAISS.load_local(INDEX_PATH, embedding_model, allow_dangerous_deserialization=True)
    print(f"   Vector store: {vector_store.index.ntotal:,} vectors")

    _model = ChatGroq(api_key=API_KEY, model_name="llama-3.3-70b-versatile",
                      temperature=0.1, max_tokens=4096, timeout=60)
    print(f"   LLM ready\n")
except Exception as e:
    print(f"ERROR loading models: {e}"); sys.exit(1)

# ── Cities ────────────────────────────────────────────────────────────────────
def load_cities():
    cities = set()
    for q in ["Pakistan","city","places","travel","tourism"]:
        try:
            for doc in vector_store.similarity_search(q, k=200):
                c = doc.metadata.get("Places_city","").strip()
                if c and len(c) > 2: cities.add(c.lower())
        except: pass
    if cities:
        lst = sorted(cities); print(f"Loaded {len(lst)} cities\n"); return lst
    fb = ["karachi","lahore","islamabad","rawalpindi","faisalabad",
          "multan","peshawar","quetta","hyderabad","abbottabad"]
    print(f"Fallback {len(fb)} cities\n"); return fb

PAKISTAN_CITIES = load_cities()
CITY_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in PAKISTAN_CITIES) + r")\b", re.IGNORECASE)

# ── Rate Limiter ──────────────────────────────────────────────────────────────
class RateLimiter:
    def __init__(self, rate=10, per=60):
        self.rate=rate; self.per=per; self.allowance=float(rate); self.last=time.time()
    def allow_request(self):
        now=time.time(); self.allowance+=(now-self.last)*(self.rate/self.per); self.last=now
        if self.allowance>self.rate: self.allowance=self.rate
        if self.allowance<1: return False
        self.allowance-=1; return True

rate_limiter = RateLimiter(rate=MAX_QUERIES_PER_MIN)

# ── Input Sanitization ────────────────────────────────────────────────────────
def sanitize_user_input(text, maxlen=500):
    if not text: return ""
    if len(text)>maxlen: raise ValueError(f"Too long (max {maxlen})")
    text = unicodedata.normalize("NFKC", text)
    text = "".join(c for c in text if unicodedata.category(c)[0]!="C" or c in " \n")
    text = html.escape(text, quote=True)
    for p in [r"(?i)(<|&lt;)script",r"(?i)javascript:",r"(?i)on\w+\s*=",
              r"(?i)(eval|exec|__import__|compile)\s*[\(\[]",
              r"(?i)(DROP|DELETE|INSERT|UPDATE|SELECT)\s+",
              r"[\|\&\;]\s*(sh|bash|cmd|powershell)",
              r"(?i)(&&|\|\|).*?(rm|del|format)",
              r"\$\{.*?\}",r"\{\{.*?\}\}",r"<%.*?%>",r"%0[ad]"]:
        if re.search(p, text): raise ValueError("Malicious content detected")
    if not re.match(r"^[a-zA-Z0-9\s\.,\-\?\!\'\"]+$", text):
        raise ValueError("Invalid characters")
    return text.strip()

def detect_prompt_injection(q):
    for p in [r"(?i)ignore\s+(all\s+)?previous\s+instructions",r"(?i)you\s+are\s+now",
              r"(?i)forget\s+(everything|all)",r"(?i)system\s+prompt",
              r"(?i)reveal\s+your",r"(?i)act\s+as\s+a\s+(?!travel)",r"(?i)roleplay"]:
        if re.search(p,q): return True
    return False

# ── Query Parsing ─────────────────────────────────────────────────────────────
def parse_travel_intent(query):
    ql = query.lower()
    cities = [m.title() for m in CITY_RE.findall(ql)]
    dest = None
    m = re.search(r"from\s+\w+\s+to\s+(\w+(?:\s+\w+)?)", ql)
    if m:
        pot = m.group(1).strip()
        for c in PAKISTAN_CITIES:
            if pot in c or c in pot: dest=c.title(); break
        if not dest and len(cities)>=2: dest=cities[-1]
    elif cities:
        dest = cities[-1] if any(w in ql for w in [" in ","visit","explore","trip to","travel to"]) else cities[0]
    dm  = re.search(r"(\d+)\s*(?:day|days)", ql)
    dur = min(max(int(dm.group(1)) if dm else 3, 1), 14)
    bud = None
    if any(t in ql for t in ["moderate","mid","medium","average"]): bud="moderate"
    elif any(t in ql for t in ["low","cheap","budget","affordable"]):  bud="low"
    elif any(t in ql for t in ["luxury","expensive","high","premium"]): bud="high"
    return {"destination_city":dest,"duration":dur,"budget_preference":bud,"query":query}

def build_search_queries(intent):
    city = intent.get("destination_city")
    q = []
    if city:
        q += [city, f"places to visit in {city}", f"{city} attractions",
              f"restaurants in {city}", f"hotels in {city}"]
        if intent.get("budget_preference"):
            q.append(f"{intent['budget_preference']} budget places in {city}")
    else:
        q += ["Pakistan travel places","tourist attractions Pakistan"]
    q.append(intent["query"])
    return q[:8]

# ── Budget ────────────────────────────────────────────────────────────────────
def normalize_budget_category(b):
    if not b or str(b).lower() in ["not specified","nan","none",""]: return "unspecified"
    bl = str(b).lower()
    nums = re.findall(r"\d+", b)
    if nums:
        avg = sum(int(n) for n in nums)/len(nums)
        return "low" if avg<500 else "moderate" if avg<2000 else "high"
    if any(t in bl for t in ["low","cheap","budget","affordable"]): return "low"
    if any(t in bl for t in ["moderate","mid","medium","average"]):  return "moderate"
    if any(t in bl for t in ["high","luxury","expensive","premium"]): return "high"
    return "unspecified"

def get_budget_emoji(cat):
    return {"low":"💵","moderate":"💳","high":"💎"}.get(cat,"💰")

def categorize_place_type(ptype):
    t = ptype.lower()
    if any(k in t for k in ["hotel","motel","lodge","inn","resort","guest house","hostel"]): return "hotel"
    if any(k in t for k in ["restaurant","cafe","coffee","food","eatery","dining",
                             "bakery","biryani","karahi","sweets","grill","bbq","dhaba"]): return "restaurant"
    return "attraction"

def normalize_place_name(name):
    n = re.sub(r"[^\w\s]","",name.lower())
    n = " ".join(n.split())
    stops = {"the","a","an","and","or","of","at","in"}
    return " ".join(w for w in n.split() if w not in stops)

# ============================================================================
# TIMING LOGIC
# ============================================================================

_ALLDAY_NORM = {
    "all-day","all day","allday","all_day",
    "fullday","full day","full-day",
}

def normalize_timing_for_filtering(raw):
    if not raw or str(raw).strip().lower() in ("nan","none","","not specified"):
        return ["all-day"]
    key = str(raw).strip().lower()
    clean = re.sub(r"[\s/,\-]+", " ", key).strip()
    if clean in _ALLDAY_NORM or key in _ALLDAY_NORM:
        return ["all-day"]
    MAP = {
        "breakfast":         ["breakfast"],
        "breakfast brunch":  ["brunch"],
        "brunch":            ["brunch"],
        "brunch meals":      ["brunch"],
        "lunch":             ["lunch"],
        "dinner":            ["dinner"],
        "dinner snacks":     ["dinner"],
        "dinner late":       ["dinner"],
        "mainmeals":         ["mainmeals"],
        "main meals":        ["mainmeals"],
        "meals":             ["meals"],
        "dessert":           ["meals"],
        "morning":           ["morning"],
        "afternoon":         ["afternoon"],
        "evening":           ["evening"],
        "night":             ["night"],
    }
    if clean in MAP: return MAP[clean]
    if key   in MAP: return MAP[key]
    if "breakfast" in key and "lunch" in key: return ["brunch"]
    if "breakfast" in key: return ["breakfast"]
    if "brunch"    in key: return ["brunch"]
    if "mainmeal"  in key or "main meal" in key: return ["mainmeals"]
    if "lunch"     in key: return ["lunch"]
    if "dinner"    in key: return ["dinner"]
    if "meal"      in key: return ["meals"]
    if "morning"   in key: return ["morning"]
    if "afternoon" in key: return ["afternoon"]
    if "evening"   in key: return ["evening"]
    if "night"     in key: return ["night"]
    return ["all-day"]

def get_timing_display(raw):
    if not raw or str(raw).strip().lower() in ("nan","none","","not specified"):
        return "All-day"
    return str(raw).strip()

def matches_timing(place_timing: List[str], required_timing: str) -> bool:
    if not place_timing: return True
    req = required_timing.lower()
    if "all-day" in place_timing: return True
    if req in place_timing: return True
    if req == "breakfast":
        return any(t in place_timing for t in ["breakfast","brunch","meals"])
    if req == "lunch":
        return any(t in place_timing for t in ["lunch","brunch","mainmeals"])
    if req == "dinner":
        return any(t in place_timing for t in ["dinner","mainmeals","meals"])
    return False

# ============================================================================
# RETRIEVE & FILTER
# ============================================================================

def retrieve_and_filter_places(intent, k_per_query=100):
    MAX_DOCS  = 600
    dest      = intent.get("destination_city")
    bud_pref  = intent.get("budget_preference")
    queries   = build_search_queries(intent)

    all_docs, seen_ids, seen_norm = [], set(), set()
    print("Searching database...")

    for q in queries:
        if len(all_docs) >= MAX_DOCS: break
        try:
            k = min(k_per_query, MAX_DOCS - len(all_docs))
            for doc in vector_store.similarity_search(q, k=k):
                name = doc.metadata.get("Places_name","").strip()
                nn   = normalize_place_name(name)
                did  = f"{name}_{doc.metadata.get('Places_city','')}"
                if nn in seen_norm or did in seen_ids: continue
                all_docs.append(doc); seen_ids.add(did); seen_norm.add(nn)
        except Exception as e: logger.warning(f"Search: {e}")

    print(f"   Raw docs: {len(all_docs)}")

    hotels, restaurants, attractions = [], [], []
    used_names, used_norm_set = set(), set()

    for doc in all_docs:
        meta   = doc.metadata
        name   = meta.get("Places_name","").strip()
        ptype  = meta.get("Places_type","").strip()
        city   = meta.get("Places_city","").strip()
        ref    = meta.get("Places_reference","").strip()
        budget = meta.get("Budget","")
        timing_raw = meta.get("timing") or meta.get("Timings") or "All-day"

        if not name or not city: continue
        nn = normalize_place_name(name)
        if nn in used_norm_set or name in used_names: continue
        if dest and city.lower().strip() != dest.lower().strip(): continue

        bcat = normalize_budget_category(budget)
        if bud_pref and bcat != "unspecified":
            order = {"low":0,"moderate":1,"high":2}
            mp = "moderate" if bud_pref=="medium" else bud_pref
            if mp in order and bcat in order:
                if abs(order[mp]-order[bcat]) > 1: continue

        used_names.add(name); used_norm_set.add(nn)
        link = ref or f"https://www.google.com/maps/search/{name.replace(' ','+' )}+{city.replace(' ','+')}"

        timing_display = get_timing_display(timing_raw)
        timing_tags    = normalize_timing_for_filtering(timing_raw)

        entry = dict(name=name, type=ptype, city=city, link=link,
                     budget=budget, budget_category=bcat,
                     timing=timing_tags,
                     timing_display=timing_display,
                     normalized_name=nn)

        cat = categorize_place_type(ptype)
        if cat == "hotel":
            hotels.append(entry)
        elif cat == "restaurant":
            restaurants.append(entry)
        else:
            attractions.append(entry)

    random.shuffle(hotels)
    random.shuffle(restaurants)
    random.shuffle(attractions)

    print(f"   Hotels:{len(hotels)} | Restaurants:{len(restaurants)} | Attractions:{len(attractions)}")

    r_dist: Dict[str,int] = {}
    for r in restaurants:
        td = r["timing_display"]
        r_dist[td] = r_dist.get(td,0)+1
    a_dist: Dict[str,int] = {}
    for a in attractions:
        td = a["timing_display"]
        a_dist[td] = a_dist.get(td,0)+1

    br=[r for r in restaurants if matches_timing(r["timing"],"breakfast")]
    lr=[r for r in restaurants if matches_timing(r["timing"],"lunch")]
    dr=[r for r in restaurants if matches_timing(r["timing"],"dinner")]
    ma=[a for a in attractions  if matches_timing(a["timing"],"morning")]
    aa=[a for a in attractions  if matches_timing(a["timing"],"afternoon")]
    ea=[a for a in attractions  if matches_timing(a["timing"],"evening")]
    na=[a for a in attractions  if matches_timing(a["timing"],"night")]

    print(f"\n   RESTAURANTS (by CSV timing):")
    for t,c in sorted(r_dist.items(),key=lambda x:x[1],reverse=True)[:12]:
        print(f"      {t!r}: {c}")
    print(f"   Breakfast:{len(br)} Lunch:{len(lr)} Dinner:{len(dr)}")
    print(f"\n   ATTRACTIONS (by CSV timing):")
    for t,c in sorted(a_dist.items(),key=lambda x:x[1],reverse=True)[:12]:
        print(f"      {t!r}: {c}")
    print(f"   Morning:{len(ma)} Afternoon:{len(aa)} Evening:{len(ea)} Night:{len(na)}\n")

    return hotels, restaurants, attractions

# ============================================================================
# SMART FREE TIME
# ============================================================================

def get_places_for_slot(places, required_timing, global_used, limit):
    result = []
    for p in places:
        if p["normalized_name"] in global_used: continue
        if matches_timing(p["timing"], required_timing):
            result.append(p)
        if len(result) >= limit: break
    return result

# ============================================================================
# CONTEXT FORMATTING
# ============================================================================

def format_context(intent, hotels, restaurants, attractions):
    dest = intent.get("destination_city","Pakistan")
    dur  = intent.get("duration",3)
    global_used: Set[str] = set()

    ctx  = f"=== {dest.upper()} | {dur} DAYS ===\n\n"

    ctx += "HOTELS (choose exactly ONE):\n"
    for i,h in enumerate(hotels[:8],1):
        e = get_budget_emoji(h["budget_category"])
        ctx += (f"H{i}. {h['name']} | {h['type']} | {h['link']} "
                f"| ({e} {h['budget_category'].upper()}) | ⏰ {h['timing_display']} ⏰\n")
    if not hotels: ctx += "  None available\n"
    ctx += "\n"

    def slot_section(label, slot_key, pool, per_day):
        needed = dur * per_day + 5
        cands  = get_places_for_slot(pool, slot_key, global_used, needed)
        for p in cands:
            global_used.add(p["normalized_name"])
        lines = f"{label}\n"
        if cands:
            for i, p in enumerate(cands, 1):
                e = get_budget_emoji(p["budget_category"])
                lines += (f"  {i}. {p['name']} | {p['type']} | {p['link']} "
                          f"| ({e} {p['budget_category'].upper()}) | ⏰ {p['timing_display']} ⏰\n")
            lines += f"  ── Total: {len(cands)} places available\n"
        else:
            lines += "  NONE — use FREE TIME for every slot in this list\n"
        lines += "\n"
        return lines, len(cands)

    ctx += "=" * 65 + "\n"
    ctx += "RESTAURANTS — use ONLY from correct slot list\n"
    ctx += "  NOTE: All-day / FullDay places valid for any meal\n"
    ctx += "  NOTE: Brunch valid for breakfast OR lunch\n"
    ctx += "  NOTE: MainMeals valid for lunch OR dinner\n"
    ctx += "  NOTE: Meals valid for breakfast OR dinner\n"
    ctx += "=" * 65 + "\n\n"

    s, br_n = slot_section("BREAKFAST LIST (9:30 AM):", "breakfast", restaurants, 1)
    ctx += s
    s, lr_n = slot_section("LUNCH LIST (2:00 PM):", "lunch", restaurants, 1)
    ctx += s
    s, dr_n = slot_section("DINNER LIST (8:30 PM):", "dinner", restaurants, 1)
    ctx += s

    ctx += "=" * 65 + "\n"
    ctx += "ATTRACTIONS — use ONLY from correct slot list\n"
    ctx += "  NOTE: All-day / FullDay places valid for any time slot\n"
    ctx += "=" * 65 + "\n\n"

    s, ma_n = slot_section("MORNING LIST (10AM-1PM):", "morning", attractions, 4)
    ctx += s
    s, aa_n = slot_section("AFTERNOON LIST (3PM-6PM):", "afternoon", attractions, 4)
    ctx += s
    s, ea_n = slot_section("EVENING LIST (7:30PM):", "evening", attractions, 1)
    ctx += s
    s, na_n = slot_section("NIGHT LIST (9:30PM+):", "night", attractions, 1)
    ctx += s

    ctx += "=" * 65 + "\n"
    ctx += f"AVAILABLE COUNTS:\n"
    ctx += f"  Breakfast:{br_n} | Lunch:{lr_n} | Dinner:{dr_n}\n"
    ctx += f"  Morning:{ma_n} | Afternoon:{aa_n} | Evening:{ea_n} | Night:{na_n}\n"
    ctx += "\n"

    morning_need   = dur * 2
    afternoon_need = dur * 4
    evening_need   = dur * 2
    night_need     = dur * 1
    br_need        = dur * 1
    lr_need        = dur * 1
    dr_need        = dur * 1

    ma_ft  = max(0, morning_need   - ma_n)
    aa_ft  = max(0, afternoon_need - aa_n)
    ea_ft  = max(0, evening_need   - ea_n)
    na_ft  = max(0, night_need     - na_n)
    br_ft  = max(0, br_need        - br_n)
    lr_ft  = max(0, lr_need        - lr_n)
    dr_ft  = max(0, dr_need        - dr_n)

    ctx += "FREE TIME TRACKING:\n"
    ctx += f"  Slots needed  — Morning:{morning_need} Afternoon:{afternoon_need} Evening:{evening_need} Night:{night_need}\n"
    ctx += f"  Slots needed  — Breakfast:{br_need} Lunch:{lr_need} Dinner:{dr_need}\n"
    ctx += f"  Available     — Morning:{ma_n} Afternoon:{aa_n} Evening:{ea_n} Night:{na_n}\n"
    ctx += f"  Available     — Breakfast:{br_n} Lunch:{lr_n} Dinner:{dr_n}\n"
    ctx += f"  FREE TIME needed — Morning:{ma_ft} Afternoon:{aa_ft} Evening:{ea_ft} Night:{na_ft}\n"
    ctx += f"  FREE TIME needed — Breakfast:{br_ft} Lunch:{lr_ft} Dinner:{dr_ft}\n"
    ctx += "\n"
    ctx += "FREE TIME RULES:\n"
    ctx += "  1. NEVER repeat a place — each place used EXACTLY ONCE.\n"
    ctx += "  2. Work through each list IN ORDER, top to bottom, one per slot.\n"
    ctx += "  3. When a list runs out mid-itinerary, switch to FREE TIME for that slot.\n"
    ctx += "  4. FREE TIME format: **TIME** – 🕐 FREE TIME: Explore or relax nearby\n"
    ctx += "  5. Meals: if Breakfast/Lunch/Dinner list exhausted, write FREE TIME for that meal.\n"
    ctx += "=" * 65 + "\n\n"

    return ctx

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """You are a Pakistan Travel Itinerary AI v4.1.

═══════════════════════════════════════════════════════════════════
RULE 1 — ZERO DUPLICATES (MOST IMPORTANT RULE)
═══════════════════════════════════════════════════════════════════
Every place in this itinerary must appear EXACTLY ONCE.
Before writing each slot, mentally check: "Have I used this place before?"
If YES → skip it, take the NEXT place from the list.
If the list is fully exhausted → write FREE TIME for that slot.
NEVER repeat a place under any circumstances.

═══════════════════════════════════════════════════════════════════
RULE 2 — USE LISTS IN ORDER, ONE PER SLOT
═══════════════════════════════════════════════════════════════════
Each list is numbered. Consume them top-to-bottom, one per time slot.
  Day 1 breakfast → use item 1 from BREAKFAST LIST
  Day 2 breakfast → use item 2 from BREAKFAST LIST
  Day 3 breakfast → use item 3 from BREAKFAST LIST
  Day 4 breakfast → list has only 3 items → FREE TIME

Same rule for ALL lists (Lunch, Dinner, Morning, Afternoon, Evening, Night).

═══════════════════════════════════════════════════════════════════
RULE 3 — FREE TIME WHEN LIST EXHAUSTED
═══════════════════════════════════════════════════════════════════
The DATA section shows "FREE TIME needed" counts per slot.
When a slot's list runs out, write:
  **TIME** – 🕐 FREE TIME: Explore or relax nearby

For meals (breakfast/lunch/dinner) when list is exhausted:
  **TIME** – 🕐 FREE TIME: Grab a meal at a local spot nearby

═══════════════════════════════════════════════════════════════════
RULE 4 — TIMING TAG
═══════════════════════════════════════════════════════════════════
Copy the ⏰ value EXACTLY as written in the data entry.
Do NOT change it. Do NOT invent it.

═══════════════════════════════════════════════════════════════════
RULE 5 — ONE HOTEL, APPEARS EXACTLY TWICE
═══════════════════════════════════════════════════════════════════
Check-in: Day 1 at 9:00 AM
Check-out: Last day at 6:00 PM
The hotel is the ONLY place allowed to appear twice.

════════════════════════════════════════════════════════
EXACT TIME SCHEDULE — FOLLOW PRECISELY EVERY DAY
════════════════════════════════════════════════════════

DAY 1 Karachi (14 entries):
1.  **9:00 AM**  – 🏨 Check-in at [Hotel](link) - Type (BUDGET) ⏰ Tag ⏰
2.  **9:30 AM**  – 🍽️ Breakfast at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
3.  **10:00 AM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← MORNING LIST item 1
4.  **11:00 AM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← MORNING LIST item 2
5.  **12:00 PM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST item 1
6.  **1:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST item 2
7.  **2:00 PM**  – 🍽️ Lunch at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
8.  **3:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST item 3
9.  **4:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST item 4
10. **5:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← EVENING LIST item 1
11. **6:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← EVENING LIST item 2
12. **7:30 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← NIGHT LIST item 1
13. **8:30 PM**  – 🍽️ Dinner at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
14. **9:30 PM**  – 🏨 Rest at Hotel

MIDDLE DAYS — Day 2 Lahore (13 entries):
1.  **9:30 AM**  – 🍽️ Breakfast at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
2.  **10:00 AM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← MORNING LIST next item
3.  **11:00 AM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← MORNING LIST next item
4.  **12:00 PM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
5.  **1:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
6.  **2:00 PM**  – 🍽️ Lunch at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
7.  **3:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
8.  **4:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
9.  **5:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← EVENING LIST next item
10. **6:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← EVENING LIST next item
11. **7:30 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← NIGHT LIST next item
12. **8:30 PM**  – 🍽️ Dinner at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
13. **9:30 PM**  – 🏨 Rest at Hotel

LAST DAY Multan (10 entries):
1.  **9:30 AM**  – 🍽️ Breakfast at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
2.  **10:00 AM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← MORNING LIST next item
3.  **11:00 AM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← MORNING LIST next item
4.  **12:00 PM** – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
5.  **2:00 PM**  – 🍽️ Lunch at [Name](link) - Type (BUDGET) ⏰ Tag ⏰
6.  **3:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
7.  **4:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
8.  **5:00 PM**  – 📍 Visit [Name](link) - Type (BUDGET) ⏰ Tag ⏰    ← AFTERNOON LIST next item
9.  **6:00 PM**  – 🏨 Check-out from [Hotel](link) - Type (BUDGET) ⏰ Tag ⏰
10. **6:30 PM**  – 🚗 Departure

════════════════════════════════════════════════════════
FORMAT RULES
════════════════════════════════════════════════════════
  Header:     ### Day 1
  Numbers:    1. 2. 3. 4. (not bullets)
  Time:       **9:00 AM** (always bold, always with AM/PM)
  Separator:  – (em dash, not hyphen)
  Link:       [Place Name](url)
  After link: - Type (💳 MODERATE) ⏰ ExactTag ⏰
  Rest line:  **9:30 PM** – 🏨 Rest at Hotel           ← no link, no tag
  Departure:  **6:30 PM** – 🚗 Departure               ← no link, no tag
  Budget:     💵 LOW  💳 MODERATE  💎 HIGH  💰 UNSPECIFIED

════════════════════════════════════════════════════════

DATA:
{context}

QUERY: {question}

Generate a complete {duration}-day itinerary.
- Work through each list IN ORDER, one item per slot, per day.
- NEVER use a place twice — hotel is the only exception (check-in + check-out).
- When a list runs out → FREE TIME for remaining slots of that type.
- Copy every ⏰ tag EXACTLY as it appears in the data entry."""

# ── Analysis ──────────────────────────────────────────────────────────────────
def analyze_itinerary(content, intent, hotels, restaurants, attractions):
    links  = re.findall(r"\[([^\]]+)\]\([^)]+\)", content)
    cin    = set(re.findall(r"Check-in at \[([^\]]+)\]", content))
    cout   = set(re.findall(r"Check-out from \[([^\]]+)\]", content))
    hp     = cin & cout
    cnts   = Counter(links)
    dups   = {n:c for n,c in cnts.items() if c>1 and n not in hp}
    dur    = intent.get("duration",3)
    days   = len(set(re.findall(r"### Day (\d+)", content)))
    br     = content.count("Breakfast")
    lu     = content.count("Lunch")
    di     = content.count("Dinner")
    ft     = content.count("FREE TIME")
    ti     = content.count("⏰")
    s  = min(25, len(links)/max(dur*10,1)*25)
    s += days/max(dur,1)*20
    s += min(20,(br+lu+di)/max(dur*3,1)*20)
    s += 20 if not dups else max(0,20-len(dups)*4)
    s += 5  if hp else 0
    s += 10 if ti>=max(len(links)//2,1) else 5
    s -= max(0, (ft - 0) * 2)
    return dict(links=len(links),days=days,exp=dur,br=br,lu=lu,di=di,
                dups=dups,dup_n=len(dups),hp=hp,ft=ft,ti=ti,score=min(100,max(0,int(s))))

def print_quality_report(a):
    print("\n" + "="*70)
    print("QUALITY REPORT v4.1")
    print("="*70)
    for h in a["hp"]: print(f"  Hotel OK: {h!r}")
    if not a["hp"]:   print("  WARNING: Hotel check-in/out not detected")
    if a["dup_n"]:
        print(f"  DUPLICATES ({a['dup_n']}):")
        for n,c in a["dups"].items(): print(f"    {n!r} x{c}")
    else: print(f"  Zero duplicates — {a['links']} unique places")
    print(f"  Days: {a['days']}/{a['exp']}")
    print(f"  Meals: {a['br']}B {a['lu']}L {a['di']}D")
    print(f"  Timing tags: {a['ti']} | Free time slots: {a['ft']}")
    if a["ft"] > a["exp"]:
        print(f"   {a['ft']} free time slots seems high — this city had enough places")
    print(f"  Score: {a['score']}/100")
    print("="*70+"\n")

# ============================================================================
# FIXED: API CALL WITH PROPER ERROR HANDLING
# ============================================================================

def invoke_llm_with_retry(prompt: str, max_attempts: int = 3):
    """
    Invoke the LLM with status-code-aware retry logic.

    - 429 RateLimitError       → wait 30s and retry (up to max_attempts)
    - 401 / 403 Auth errors    → print clear message, do NOT retry
    - 500 / 502 / 503 Server   → wait and retry with backoff
    - Other APIStatusError     → print status code + message, do NOT retry
    - Connection / Timeout     → retry with backoff
    """
    last_error = None

    for attempt in range(max_attempts):
        try:
            response = _model.invoke(prompt)
            return response

        except Exception as e:
            last_error = e
            err_type   = type(e).__name__
            err_str    = str(e).lower()

            # ── Groq-specific typed errors (preferred path) ──────────────────
            if GROQ_ERRORS_AVAILABLE:
                if isinstance(e, RateLimitError):
                    wait = 30 * (attempt + 1)
                    print(f"  Rate limit hit (429) — waiting {wait}s before retry {attempt+1}/{max_attempts}...")
                    time.sleep(wait)
                    continue

                if isinstance(e, AuthenticationError):
                    print("  Auth error (401/403) — check your GROQ_API_KEY in .env")
                    logger.error(f"Auth error: {e}")
                    return None

                if isinstance(e, APIConnectionError):
                    wait = 5 * (2 ** attempt)
                    print(f"  Connection error — retry {attempt+1}/{max_attempts} in {wait}s...")
                    time.sleep(wait)
                    continue

                if isinstance(e, GroqAPIStatusError):
                    status = getattr(e, 'status_code', None)
                    if status in (500, 502, 503, 504):
                        wait = 10 * (attempt + 1)
                        print(f"  Server error ({status}) — retry {attempt+1}/{max_attempts} in {wait}s...")
                        time.sleep(wait)
                        continue
                    else:
                        # Non-retryable API error (400, 404, etc.)
                        print(f"  API error (status {status}): {e}")
                        logger.error(f"APIStatusError {status}: {e}")
                        return None

            # ── Fallback: string-based detection ────────────────────────────
            if "429" in err_str or "rate" in err_str or "ratelimit" in err_str:
                wait = 30 * (attempt + 1)
                print(f"  Rate limit detected — waiting {wait}s before retry {attempt+1}/{max_attempts}...")
                time.sleep(wait)
                continue

            if "401" in err_str or "403" in err_str or "authentication" in err_str or "unauthorized" in err_str:
                print("  Authentication error — check your GROQ_API_KEY in .env")
                logger.error(f"Auth error: {e}")
                return None

            if any(x in err_str for x in ["500", "502", "503", "504", "server error"]):
                wait = 10 * (attempt + 1)
                print(f"  Server error — retry {attempt+1}/{max_attempts} in {wait}s...")
                time.sleep(wait)
                continue

            if any(x in err_type.lower() for x in ["connection", "timeout", "network"]):
                wait = 5 * (2 ** attempt)
                print(f"  {err_type} — retry {attempt+1}/{max_attempts} in {wait}s...")
                time.sleep(wait)
                continue

            # ── Unknown error — show it clearly, do not retry ────────────────
            print(f"  Unexpected error ({err_type}): {e}")
            logger.error(f"LLM error {err_type}: {e}", exc_info=True)
            return None

    print(f"  All {max_attempts} attempts failed. Last error: {type(last_error).__name__}")
    logger.error(f"All retry attempts failed: {last_error}")
    return None

# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    print("Pakistan Travel Planner v4.1")
    print("="*70)
    print("Examples:")
    print("  Plan a 3 day trip to Karachi with low budget")
    print("  Create 4 days itinerary Lahore moderate budget")
    print("\nType exit to quit\n")

    while True:
        try:
            raw = input("You: ").strip()
            if raw.lower() == "exit": print("Goodbye!"); break
            if not rate_limiter.allow_request():
                print("Rate limit — wait 60s\n"); time.sleep(5); continue
            try:
                if len(raw)>500: print("Too long\n"); continue
                q = sanitize_user_input(raw)
                if detect_prompt_injection(q): print("Travel queries only\n"); continue
            except ValueError as e: print(f"Invalid: {e}\n"); continue

            print("\nAnalyzing...")
            intent = parse_travel_intent(q)
            print(f"  Dest:{intent['destination_city']} Days:{intent['duration']} Budget:{intent['budget_preference']}\n")

            hotels, restaurants, attractions = retrieve_and_filter_places(intent)
            if not hotels: print("No hotels found\n"); continue

            ctx = format_context(intent, hotels, restaurants, attractions)
            if len(ctx) > 14000: ctx = "\n".join(ctx.split("\n")[:420])

            prompt = PROMPT_TEMPLATE.format(context=ctx, question=q, duration=intent["duration"])
            print("Generating itinerary...")

            # ── FIXED: use the new retry function ────────────────────────────
            resp = invoke_llm_with_retry(prompt)

            if resp is None:
                print("Could not generate itinerary. Please try again.\n")
                continue

            print("\n" + "="*70+"\n YOUR ITINERARY\n"+"="*70)
            print(resp.content)
            print("="*70)
            print_quality_report(analyze_itinerary(resp.content, intent, hotels, restaurants, attractions))

        except KeyboardInterrupt: print("\nGoodbye!"); break
        except Exception as e:
            logger.error(str(e), exc_info=True)
            print(f"Error: {type(e).__name__}: {e} — try again\n")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\nGoodbye!")
    except Exception as e:
        logger.critical(str(e), exc_info=True)
        print(f"Fatal: {e}"); sys.exit(1)

def parse_itinerary_to_json(content):
    """
    Convert LLM text → structured JSON (WITH links + type)
    """

    import re

    days = []
    current_day = None
    seen_days = set()

    lines = content.split("\n")

    for line in lines:
        line = line.strip()

        # ------------------------
        # Detect Day
        # ------------------------
        if line.startswith("### Day"):
            day_name = line.replace("### ", "").strip()

    # ❌ Skip duplicate days
            if day_name in seen_days:
                continue

            seen_days.add(day_name)

            if current_day:
                days.append(current_day)

            current_day = {
                "day": day_name,
                "schedule": []
            }

        # ------------------------
        # Detect activity lines
        # ------------------------
        elif re.match(r"^\d+\.", line) and current_day:
            try:
                # Extract time
                time_match = re.search(r"\*\*(.*?)\*\*", line)
                time = time_match.group(1) if time_match else "N/A"

                # Remove numbering + time
                raw_activity = re.sub(r"^\d+\.\s*\*\*.*?\*\*\s*–\s*", "", line)

                # ------------------------
                # EXTRACT LINK + NAME
                # [Place Name](link)
                # ------------------------
                link_match = re.search(r"\[(.*?)\]\((.*?)\)", raw_activity)

                place_name = None
                link = None

                if link_match:
                    place_name = link_match.group(1)
                    link = link_match.group(2)

                # ------------------------
                # EXTRACT TYPE
                # Type (LOW / MODERATE / HIGH)
                # ------------------------
                type_match = re.search(
    r"Type\s*\(?\s*(?:💵|💳|💎)?\s*(LOW|MODERATE|HIGH)\s*\)?",
    raw_activity,
    re.IGNORECASE
)

                budget_type = None
                if type_match:
                    budget_type = type_match.group(1).lower()

                # ------------------------
                # CLEAN TEXT (BUT KEEP MEANING)
                # ------------------------
                clean_activity = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", raw_activity)
                clean_activity = re.sub(r"-\s*Type.*", "", clean_activity)
                clean_activity = re.sub(r"[^\w\s:,.-]", "", clean_activity).strip()

                current_day["schedule"].append({
                    "time": time,
                    "activity": clean_activity,   # clean text for UI
                    "place": place_name,
                    "link": link,
                    "type": budget_type,
                    "raw": raw_activity           # optional (debug / future)
                })

            except Exception:
                continue

    if current_day:
        days.append(current_day)

    return days

# ================= BACKEND WRAPPER FUNCTION =================
def generate_itinerary_llm(destination, days, budget, interests):
    """
    Wrapper function for FastAPI route.
    Keeps ALL RAG logic intact.
    """

    try:
        # ------------------------
        # Build user query (same as your old system)
        # ------------------------
        user_query = f"Generate a {days}-day trip to {destination} with interests {', '.join(interests)} and budget {budget}."

        # ------------------------
        # Rate limit check
        # ------------------------
        if not rate_limiter.allow_request():
            raise Exception("Rate limit exceeded. Try again later.")

        # ------------------------
        # Sanitize input (existing logic)
        # ------------------------
        user_query = sanitize_user_input(user_query)

        if detect_prompt_injection(user_query):
            raise Exception("Invalid query detected")

        # ------------------------
        # Parse intent (existing RAG logic)
        # ------------------------
        intent = parse_travel_intent(user_query)

        # Override destination + days (IMPORTANT for your app)
        intent["destination_city"] = destination
        intent["duration"] = days

        # ------------------------
        # Retrieve data
        # ------------------------
        hotels, restaurants, attractions = retrieve_and_filter_places(intent)

        if not hotels:
            raise Exception("No hotels found for this destination")

        # ------------------------
        # Build context
        # ------------------------
        context = format_context(intent, hotels, restaurants, attractions)

        if len(context) > 14000:
            context = "\n".join(context.split("\n")[:420])

        # ------------------------
        # Create prompt
        # ------------------------
        prompt = PROMPT_TEMPLATE.format(
            context=context,
            question=user_query,
            duration=intent["duration"]
        )

        # ------------------------
        # Call LLM (with retry logic)
        # ------------------------
        response = invoke_llm_with_retry(prompt)

        if response is None:
            raise Exception("LLM failed after retries")

        content = response.content
        
        structured_output = parse_itinerary_to_json(content)
        return structured_output

    except Exception as e:
        raise Exception(f"LLM generation failed: {str(e)}")