# =====================================================================================
#  CATALOG MATCHING  -  Shops catalog vs Dmart                  (Google Colab + Google Sheets)
#  Run the cells from top to bottom. Change only CELL 2 (SETTINGS).
#
#  Stage 1  Clean      one row per product code, barcodes checked, a STANDARDISED copy of every
#                      title is made for comparing (the original titles are never changed)
#  Stage 2  Find       for each Shops product, look for Dmart products by MPC, barcode and title
#                      (title = the 3 closest Dmart titles out of all Dmart products)
#  Stage 3  Compare    every pair gets similarity scores and a STAGE:
#                        1 EXACT
#                        2 EXACT (after standardisation)
#                        3 HIGH SIMILARITY
#                        4 MEDIUM SIMILARITY
#                        5 DIFFERENT / CHECK
#                        (details of every check are in the "checks" column)
#                        6 DIFFERENT SIZE / PACK / VARIANT
#                      one Dmart product is selected per Shops product: MPC > barcode > title.
#                      Same MPC or barcode but a different product -> FLAGGED.
#  Stage 4  Shops vs Shops   Shops products with no Dmart match are compared with each other
#                            to show possible duplicates.
#
#  NOTHING is overwritten or merged: Dmart and Shops titles are shown side by side,
#  with a "Your decision" column. Every Shops code is counted: matched + no match + dropped = start.
# =====================================================================================

# %% ---------------------------------------------------------------- CELL 1: install + sign in
!pip -q install rapidfuzz gspread

from google.colab import auth
auth.authenticate_user()
import gspread
from google.auth import default
creds, _ = default()
gc = gspread.authorize(creds)
print("Signed in to Google.")


# %% ---------------------------------------------------------------- CELL 2: SETTINGS (edit this cell)
from types import SimpleNamespace
C = SimpleNamespace()

# ---- where the data is: a Google Sheet link, or a file path (CSV / Excel) in Colab or Drive
C.DMART_SOURCE = "https://docs.google.com/spreadsheets/d/PASTE_DMART_SHEET_ID/edit"
C.DMART_TAB    = "Catalog Data - Dmart"     # tab name inside the Google Sheet (ignored for CSV)
C.SHOPS_SOURCE = "https://docs.google.com/spreadsheets/d/PASTE_SHOPS_SHEET_ID/edit"
C.SHOPS_TAB    = "Catalog Data - Shops"

# ---- where results go: Google Sheets created in your Drive (re-used on every run)
C.OUTPUT_PREFIX    = "Catalog Matching - "
C.OUTPUT_FOLDER_ID = ""                      # optional Drive folder ID; empty = My Drive

# ---- column names: the first name found in the file is used
C.COLUMNS = {
    "mpc":      ["master_code", "master_product_code", "master product code", "mpc", "master code"],
    "barcode":  ["barcode", "shops_barcode", "dmart_barcode", "barcodes", "ean", "gtin"],
    "title":    ["product_name_english", "product_name", "product name", "pim_product_name_english", "title", "name"],
    "brand":    ["brand_name", "brand name", "brand"],
    "price":    ["catalog_price_local", "price", "selling_price", "selling price", "mrp"],
    "image":    ["image_url", "image url", "catalog_image_url", "image"],
    "created":  ["product_created_date_local", "product_created_date", "created_date", "created date", "created_at"],
    "category": ["pim_level_one", "category", "level_one"],
    "active":   ["is_currently_active", "active", "is_active"],
}

# ---- stage settings
C.HIGH = 85                  # title confidence >= 85 -> stage 3 HIGH (if size/pack/variant agree)
C.MEDIUM = 70                # title confidence 70-85 -> stage 4 MEDIUM; below 70 -> stage 5
C.BRAND_MIN = 60             # brand score below this -> brand differs -> stage 5
C.SIZE_TOLERANCE = 0.03      # 500g = 0.5kg; 500g vs 515g = same; 500g vs 550g = different
C.PRICE_GAP = 2.0            # one price 2x the other (or more) -> flagged, stage 4 at best
C.TITLE_CANDIDATES = 3       # closest Dmart titles looked at for each Shops product
C.SHOPS_CANDIDATES = 5       # closest other Shops titles looked at in stage 4
C.MIN_TEXT_SIMILARITY = 0.45 # 0-1: titles less alike than this are not looked at
C.DIFFERENT_PRODUCT_BELOW = 60   # same MPC/barcode is flagged "DIFFERENT PRODUCT" if stage 6, brand differs or confidence < 60
C.BOTH_SIDES_OK = 90         # each title has a word the other lacks (Mint vs Eucalyptus): stage 5 unless confidence >= 90
# weights of the title confidence (they add up to 1)
C.WEIGHTS = {"levenshtein": 0.15, "jaro_winkler": 0.10, "token_sort": 0.20, "token_set": 0.20,
             "word_overlap": 0.15, "coverage": 0.10, "brand": 0.10}


# %% ---------------------------------------------------------------- CELL 3: helpers (no need to edit)
import re, html, time, itertools, unicodedata
from collections import defaultdict
import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein, JaroWinkler

DROPPED = []


def log_dropped(rows):
    for r in rows:
        r.setdefault("run_date", pd.Timestamp.today().strftime("%d-%b-%Y"))
    DROPPED.extend(rows)


# ---------------------------------------------------------------- Google Sheets in / out
def _retry(fn, *a, **k):
    for wait in (5, 15, 30, 60, 90):
        try:
            return fn(*a, **k)
        except gspread.exceptions.APIError as e:
            if any(c in str(e) for c in ("429", "500", "503")):
                print(f"   Google busy, waiting {wait}s ..."); time.sleep(wait)
            else:
                raise
    return fn(*a, **k)


def read_table(source, tab):
    """Google Sheet link -> that tab.  Otherwise a CSV / Excel path."""
    if str(source).startswith("http"):
        sh = _retry(gc.open_by_url, source)
        ws = sh.worksheet(tab) if tab else sh.sheet1
        # raw cell values: a barcode shown as "8.96E+12" still comes back as all 13 digits
        values = _retry(ws.get_all_values, value_render_option="UNFORMATTED_VALUE")
        values = [["" if v is None else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)) for v in row]
                  for row in values]
        width = max(len(r) for r in values)
        values = [r + [""] * (width - len(r)) for r in values]
        head, body = values[0], values[1:]
        seen = {}
        for i, h in enumerate(head):
            h = h.strip() or f"col_{i+1}"
            seen[h] = seen.get(h, 0) + 1
            head[i] = h if seen[h] == 1 else f"{h}_{seen[h]}"
        return pd.DataFrame(body, columns=head)
    if str(source).lower().endswith(".csv"):
        return pd.read_csv(source, dtype=str, keep_default_na=False)
    return pd.read_excel(source, sheet_name=tab or 0, dtype=str, keep_default_na=False)


def find_columns(df, label):
    lower = {c.strip().lower(): c for c in df.columns}
    found = {}
    for field, options in C.COLUMNS.items():
        for o in options:
            if o.strip().lower() in lower:
                found[field] = lower[o.strip().lower()]
                break
    for must in ("mpc", "title"):
        if must not in found:
            raise SystemExit(f"{label}: could not find the '{must}' column. Columns: {list(df.columns)}. "
                             f"Add the name to C.COLUMNS in the SETTINGS cell.")
    print(f"  {label} columns used: " + ", ".join(f"{k}={v}" for k, v in found.items()))
    return found


def open_output(name):
    title = C.OUTPUT_PREFIX + name
    try:
        return _retry(gc.open, title)
    except gspread.exceptions.SpreadsheetNotFound:
        return _retry(gc.create, title, folder_id=C.OUTPUT_FOLDER_ID or None)


def _cell(v):
    """Numbers stay numbers (so they sort); everything else - barcodes too - is sent as text."""
    if v is None:
        return ""
    if isinstance(v, (list, set, tuple)):
        return ", ".join(map(str, v))
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return "" if np.isnan(v) else float(v)
    return str(v)


def write_book(name, tabs):
    """tabs: [(tab name, DataFrame), ...] or (tab name, DataFrame, dropdown options for 'Your decision')."""
    sh = open_output(name)
    old = {ws.title: ws for ws in sh.worksheets()}
    for item in tabs:
        tab, df = item[0], item[1]
        options = item[2] if len(item) > 2 else None
        rows, cols = len(df) + 1, max(len(df.columns), 1)
        ws = old.get(tab) or _retry(sh.add_worksheet, title=tab, rows=rows, cols=cols)
        _retry(ws.clear)
        _retry(ws.resize, rows=rows, cols=cols)
        values = [[str(c) for c in df.columns]] + [[_cell(v) for v in row] for row in df.itertuples(index=False)]
        for s in range(0, len(values), 5000):            # big tabs go up in parts
            _retry(ws.update, range_name=f"A{s + 1}", values=values[s:s + 5000], value_input_option="RAW")
        _retry(ws.format, f"A1:{gspread.utils.rowcol_to_a1(1, cols)}",
               {"textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "backgroundColor": {"red": 0.12, "green": 0.22, "blue": 0.39}})
        _retry(ws.freeze, rows=1)
        if options and "Your decision" in df.columns and len(df):
            ci = list(df.columns).index("Your decision")
            rng = {"sheetId": ws.id, "startRowIndex": 1, "endRowIndex": rows, "startColumnIndex": ci, "endColumnIndex": ci + 1}
            _retry(sh.batch_update, {"requests": [
                {"setDataValidation": {"range": rng, "rule": {"condition": {"type": "ONE_OF_LIST", "values": [
                    {"userEnteredValue": o} for o in options]}, "showCustomUi": True, "strict": False}}},
                {"repeatCell": {"range": rng, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1, "green": 0.95, "blue": 0.8}}},
                                "fields": "userEnteredFormat.backgroundColor"}}]})
        old[tab] = ws
    wanted = {item[0] for item in tabs}
    for t, ws in list(old.items()):
        if t not in wanted and t in ("Sheet1", "Sheet 1") and len(old) > 1:
            _retry(sh.del_worksheet, ws)
    print(f"   -> {sh.title}: {sh.url}")
    return sh


# ============================================================ barcodes
def clean_barcode(b):
    b = re.sub(r"\D", "", str(b))
    return b.lstrip("0")

def barcode_is_valid(b):
    """Real GTIN barcodes (8/12/13/14 digits) end with a check digit. Store-made codes fail this."""
    if not b or len(b) < 8 or len(b) > 14:
        return False
    d = [int(x) for x in b[::-1]]
    total = sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(d[1:]))
    return (10 - total % 10) % 10 == d[0]

def split_barcodes(text):
    parts = re.split(r"[,;/|\s]+", str(text))
    return [clean_barcode(p) for p in parts if clean_barcode(p)]


# ============================================================ titles
SPELLING = {  # written the same way after cleaning
    "flavoured": "flavor", "flavored": "flavor", "flavour": "flavor", "flavours": "flavor",
    "colour": "color", "colours": "color", "yoghurt": "yogurt", "fibre": "fiber",
    "face wash": "facewash", "hand wash": "handwash", "body wash": "bodywash",
    "tooth paste": "toothpaste", "tooth brush": "toothbrush", "aloevera": "aloe vera",
    "extra large": "xl", "x-large": "xl", "x large": "xl", "xx-large": "xxl", "xx large": "xxl",
    "low-fat": "low fat", "un-salted": "unsalted", "sugar-free": "sugar free",
}
# words that do not tell products apart
FILLER = set("""the and with for of in a an by new pack packet pouch bottle tin jar box bag can carton
             promo offer imported import pc pcs piece pieces unit units x original regular classic uht""".split())
# words that DO tell products apart: if each side has a different one, they are different products
VARIANT = set("""chocolate choco strawberry mango banana vanilla caramel coffee mocha honey lemon lime orange apple
             grape peach pineapple watermelon guava cherry mint menthol coconut almond pista pistachio rose jasmine
             lavender salted unsalted sweet sweetened unsweetened sugar diet zero lite light low full fat cream skimmed
             black white red blue green pink purple yellow brown grey gray gold silver
             men women kids baby adult junior small medium large xl xxl xs mini jumbo king
             spicy hot mild plain masala bbq cheese garlic chilli chili tomato onion
             shampoo conditioner soap lotion gel oil spray serum powder""".split())
# medicine / product forms: compared only when BOTH titles name one (a title often leaves it out)
FORMS = {"tablet": "tablet", "tab": "tablet", "capsule": "capsule", "cap": "capsule", "syrup": "syrup",
         "suspension": "suspension", "drop": "drops", "drops": "drops", "sachet": "sachet", "injection": "injection",
         "ointment": "ointment", "inhaler": "inhaler", "suppository": "suppository", "lozenge": "lozenge"}

def fix_text(s):
    s = html.unescape(str(s))                                  # "Kellogg&#039;s" -> "Kellogg's"
    if "Ã" in s or "â€" in s:
        try:
            s = s.encode("latin1").decode("utf8")
        except Exception:
            pass
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return s

def clean_title(s):
    s = fix_text(s).lower()
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"(\w)'s\b", r"\1s", s).replace("'", "")
    s = s.replace("&", " and ")
    s = re.sub(r"(\d),(\d{3})", r"\1\2", s)                    # 1,000 -> 1000
    for k, v in SPELLING.items():
        s = re.sub(rf"(?<![a-z]){re.escape(k)}(?![a-z])", v, s)
    s = re.sub(r"(\d)\s*\+\s*(\d)", r"\1/\2", s)                # 10mg + 160mg -> 10mg/160mg
    s = re.sub(r"\s+-\s*\d{4,7}\s*$", " ", s)                      # shop item id at the end: "... 500ml - 301922"
    s = re.sub(r"\(\s*\d{4,}\s*\)", " ", s)                          # "(00001)"
    return re.sub(r"\s+", " ", s).strip()

def stem(w):
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss") and not any(ch.isdigit() for ch in w):
        return w[:-1]
    return w


# ============================================================ size / pack / variant numbers
UNITS = {"g": ("g", 1), "gm": ("g", 1), "gms": ("g", 1), "gr": ("g", 1), "grm": ("g", 1), "gram": ("g", 1), "grams": ("g", 1),
         "kg": ("g", 1000), "kgs": ("g", 1000), "kilo": ("g", 1000),
         "ml": ("ml", 1), "mls": ("ml", 1), "cl": ("ml", 10),
         "l": ("ml", 1000), "lt": ("ml", 1000), "ltr": ("ml", 1000), "ltrs": ("ml", 1000),
         "litre": ("ml", 1000), "liter": ("ml", 1000), "litres": ("ml", 1000), "liters": ("ml", 1000),
         "oz": ("g", 28.35)}
UNIT_RE = "|".join(sorted(UNITS, key=len, reverse=True))
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(" + UNIT_RE + r")(?![a-z])")
MULTI_RE = re.compile(r"(\d{1,3})\s*(?:pcs?|pieces?|packs?|packets?|bottles?|cans?|units?)?\s*[x×\*]\s*\(?(\d+(?:\.\d+)?)\s*(" + UNIT_RE + r")(?![a-z])")
MULTI_RE2 = re.compile(r"(\d+(?:\.\d+)?)\s*(" + UNIT_RE + r")\)?\s*[x×\*]\s*(\d{1,3})(?![\d.])")
COUNT_WORDS = r"pieces?|pcs?|tablets?|tabs?|capsules?|caps|sachets?|sheets?|rolls?|bags?|wipes?|pads?|diapers?|bars?|eggs?|count|ct|slices?|units?|packets?|packs?|cans?|bottles?"
COUNT_RE = re.compile(r"(?<![\d.])(\d{1,4})\s*(" + COUNT_WORDS + r")(?![a-z])")
PACKOF_RE = re.compile(r"\b(?:pack|box|set|carton|bundle)\s*of\s*(\d{1,3})\b")
XCOUNT_RE = re.compile(r"(?<![a-z0-9])[x×\*]\s*(\d{1,4})(?![\d.a-z])")
STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|iu|%|mah|w|v|mm|cm|inch|in|ply|spf)(?![a-z])")

def read_attributes(title):
    """From a title, read: size (one unit, in g or ml), pack count, item count, and other numbers."""
    t = clean_title(title)
    sizes, pack = {}, 1
    for rx, (ni, vi, ui) in ((MULTI_RE, (1, 2, 3)), (MULTI_RE2, (3, 1, 2))):
        m = rx.search(t)
        if m:
            unit, mult = UNITS[m.group(ui)]
            pack = int(m.group(ni))
            sizes.setdefault(unit, set()).add(round(float(m.group(vi)) * mult, 3))
            t2 = rx.sub(" ", t)
            break
    else:
        t2 = t
        m = PACKOF_RE.search(t)
        if m:
            pack = int(m.group(1))
    for m in SIZE_RE.finditer(t2):
        unit, mult = UNITS[m.group(2)]
        sizes.setdefault(unit, set()).add(round(float(m.group(1)) * mult, 3))
    rest = SIZE_RE.sub(" ", t2)
    counts = {int(m.group(1)) for m in COUNT_RE.finditer(rest) if int(m.group(1)) >= 1}   # "1 sachet" vs "30 sachets" counts too
    # "Panadol tablets x 20" -> 20 items (only when the title names a count word)
    if re.search(r"(?<![a-z])(" + COUNT_WORDS + r")(?![a-z])", rest):
        for m in XCOUNT_RE.finditer(rest):
            counts.add(int(m.group(1)))
        rest = XCOUNT_RE.sub(" ", rest)
    strengths = {m.group(0).replace(" ", "") for m in STRENGTH_RE.finditer(rest)}
    rest = COUNT_RE.sub(" ", STRENGTH_RE.sub(" ", PACKOF_RE.sub(" ", rest)))
    other_numbers = set(re.findall(r"(?<![a-z])\d+(?:\.\d+)?(?![a-z])", rest)) - {"1"}
    other_numbers |= set(re.findall(r"(?:#|\bno\.?\s?)(\d+)\b", t))          # shade "#1" / "No. 1" counts, even 1
    words = [stem(w) for w in re.sub(r"[^a-z0-9 ]", " ", rest).split()]
    words = [w for w in words if not w.isdigit() and w not in FILLER]
    forms = {FORMS[w] for w in words if w in FORMS}
    words = [w for w in words if w not in FORMS]
    return dict(clean=t, sizes=sizes, pack=pack, counts=counts, strengths=strengths,
                numbers=other_numbers, words=words, forms=forms)

def size_text(sizes):
    return ", ".join(f"{v:g}{u}" for u, vs in sizes.items() for v in sorted(vs))


def to_number(x):
    try:
        v = float(re.sub(r"[^\d.]", "", str(x)))
        return v if v > 0 else None
    except ValueError:
        return None


# ============================================================ closest titles (no size buckets)
def nearest_titles(query_texts, target_texts, k, same_list=False):
    """
    For each query title, find the k most similar target titles (character-piece TF-IDF + cosine).
    Searches the whole target list - nothing is grouped by size.
    Returns list of (query_index, target_index, similarity).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 4), min_df=1, sublinear_tf=True)
    vec.fit(list(target_texts) + ([] if same_list else list(query_texts)))
    T = vec.transform(target_texts)
    Q = T if same_list else vec.transform(query_texts)
    pairs = []
    kk = k + 1 if same_list else k
    TT = T.T.tocsc()
    for s in range(0, Q.shape[0], 1000):
        S = (Q[s:s + 1000] @ TT).tocsr()          # stays sparse: low memory even for 80k x 80k
        for r in range(S.shape[0]):
            lo, hi = S.indptr[r], S.indptr[r + 1]
            if lo == hi:
                continue
            vals, cols = S.data[lo:hi], S.indices[lo:hi]
            take = np.argsort(-vals)[:kk]
            qi = s + r
            for j in take:
                ti, sim = int(cols[j]), float(vals[j])
                if same_list and ti == qi:
                    continue
                if sim >= C.MIN_TEXT_SIMILARITY:
                    pairs.append((qi, ti, round(sim, 3)))
    return pairs



# ---------------------------------------------------------------- standardised title + the 6 stages
STAGES = {1: "1 EXACT", 2: "2 EXACT (after standardisation)", 3: "3 HIGH SIMILARITY", 4: "4 MEDIUM SIMILARITY",
          5: "5 DIFFERENT / CHECK", 6: "6 DIFFERENT SIZE / PACK / VARIANT"}
JUNK_BRANDS = {"", "unbranded", "unknown", "unknownbrand", "privatelabel", "nobrand", "nonbrand", "generic", "nan", "none", "others"}


def std_title(a):
    """The standardised copy of a title that is used for comparing (shown in the results)."""
    parts = list(a["words"]) + sorted(a["strengths"]) + sorted(a["numbers"])
    parts += [f"{v:g}{u}" for u, vs in a["sizes"].items() for v in sorted(vs)]
    if a["pack"] > 1:
        parts.append(f"pack of {a['pack']}")
    parts += [f"{n} pcs" for n in sorted(a["counts"])] + sorted(a["forms"])
    return " ".join(parts)


def name_key(a):
    """Same words in any order + same size/pack/count/strength/number = the same name."""
    return (" ".join(sorted(set(a["words"]))) + "|" + " ".join(sorted(f"{v:g}{u}" for u, vs in a["sizes"].items() for v in vs))
            + f"|{a['pack']}|{sorted(a['counts'])}|{sorted(a['strengths'])}|{sorted(a['numbers'])}|{sorted(a['forms'])}")


def _brand(s):
    return re.sub(r"[^a-z0-9]", "", fix_text(s).lower())


def brand_score(a, b):
    """0-100. Uses the brand columns when both are real brands, otherwise the first words of the titles."""
    ba, bb = _brand(a["brand"]), _brand(b["brand"])
    wa, wb = a["feat"]["words"], b["feat"]["words"]
    ja, jb = "".join(wa), "".join(wb)
    if ba not in JUNK_BRANDS and bb not in JUNK_BRANDS:
        if ba == bb or ba in jb or bb in ja:
            return 100.0
        return float(fuzz.ratio(ba, bb))
    one = ba if ba not in JUNK_BRANDS else (bb if bb not in JUNK_BRANDS else "")
    if one and one in ja and one in jb:
        return 100.0
    if not wa or not wb:
        return 50.0
    a1, b1 = wa[0], wb[0]
    a2, b2 = a1 + (wa[1] if len(wa) > 1 else ""), b1 + (wb[1] if len(wb) > 1 else "")
    return float(max(fuzz.ratio(a1, b1), fuzz.ratio(a2, b1), fuzz.ratio(a1, b2), fuzz.ratio(a2, b2)))


def _found_in(w, others):
    return w in others or (len(w) > 3 and any(fuzz.ratio(w, x) >= 85 for x in others))


def compare(a, b):
    """
    a, b: dict(title, brand, price, feat, std).  Returns every score, every check, the stage and the flags.
    Title confidence = weighted mix of 7 scores (all 0-100):
      levenshtein   letters to change to turn one standardised title into the other
      jaro_winkler  like levenshtein, but rewards titles that START the same way
      token_sort    word order does not matter
      token_set     extra words on one side do not count against (a shorter title inside a longer one)
      word_overlap  share of all words found on both sides (spelling mistakes allowed)
      coverage      share of the SHORTER title's words found in the longer one
      brand         same brand?
    """
    A, B = a["feat"], b["feat"]
    wa, wb = A["words"], B["words"]
    sa, sb = " ".join(wa), " ".join(wb)
    s = dict(levenshtein=Levenshtein.normalized_similarity(a["std"], b["std"]) * 100,
             jaro_winkler=JaroWinkler.similarity(a["std"], b["std"]) * 100,
             token_sort=fuzz.token_sort_ratio(sa, sb), token_set=fuzz.token_set_ratio(sa, sb))
    setA, setB = set(wa), set(wb)
    in_b = {w for w in setA if _found_in(w, setB)}
    in_a = {w for w in setB if _found_in(w, setA)}
    s["word_overlap"] = (len(in_b) + len(in_a)) / (len(setA) + len(setB)) * 100 if setA or setB else 0
    small, big = (setA, setB) if len(setA) <= len(setB) else (setB, setA)
    s["coverage"] = sum(1 for w in small if _found_in(w, big)) / len(small) * 100 if small else 0
    s["brand"] = brand_score(a, b)
    conf = sum(C.WEIGHTS[k] * s[k] for k in C.WEIGHTS)

    hard, soft = [], []          # hard = a real difference (stage 6); soft = needs a look (stage 4 at best)
    info = []                    # shown, but does not lower the stage
    # grammage
    common = set(A["sizes"]) & set(B["sizes"])
    if A["sizes"] and B["sizes"]:
        same = any(abs(x - y) / max(x, y) <= C.SIZE_TOLERANCE for u in common for x in A["sizes"][u] for y in B["sizes"][u])
        size_check = "Same" if same else "Different"
        if not same:
            hard.append(f"SIZE DIFF ({size_text(A['sizes'])} vs {size_text(B['sizes'])})")
    elif A["sizes"] or B["sizes"]:
        size_check = "Missing on one side"; soft.append("SIZE MISSING ON ONE SIDE")
    else:
        size_check = "No size in either"
    # pack / item count ("15 x 21.6g" and "15 packets" both mean 15)
    qa = set(A["counts"]) | ({A["pack"]} if A["pack"] > 1 else set())
    qb = set(B["counts"]) | ({B["pack"]} if B["pack"] > 1 else set())
    pack_check = "Same"
    if qa and qb and not (qa & qb) and not (qa == {1} and not B["counts"]) and not (qb == {1} and not A["counts"]):
        pack_check = "Different"; hard.append(f"PACK/COUNT DIFF ({sorted(qa)} vs {sorted(qb)})")
    elif (A["pack"] > 1 and not qb) or (B["pack"] > 1 and not qa):
        pack_check = "Different"; hard.append(f"PACK DIFF ({A['pack']} vs {B['pack']})")
    elif qa ^ qb and (qa - {1} or qb - {1}):
        pack_check = "Missing on one side"; soft.append("PACK/COUNT ON ONE SIDE ONLY")
    # variant: strength (mg, %, mAh ...), shade/model numbers, flavour/colour words, medicine form, origin
    variant = []
    if A["strengths"] and B["strengths"] and A["strengths"] != B["strengths"]:
        variant.append(f"STRENGTH DIFF ({', '.join(sorted(A['strengths']))} vs {', '.join(sorted(B['strengths']))})")
    elif A["strengths"] != B["strengths"]:
        soft.append("STRENGTH ON ONE SIDE ONLY")
    na_, nb_ = A["numbers"] - B["numbers"], B["numbers"] - A["numbers"]
    if na_ and nb_:
        variant.append(f"SHADE/MODEL NO. DIFF ({', '.join(sorted(A['numbers']))} vs {', '.join(sorted(B['numbers']))})")
    elif na_ or nb_:
        soft.append(f"NUMBER ON ONE SIDE ONLY ({', '.join(sorted(na_ | nb_))})")
    va, vb = setA & VARIANT, setB & VARIANT
    if va - vb and vb - va:
        variant.append(f"VARIANT DIFF ({', '.join(sorted(va - vb))} vs {', '.join(sorted(vb - va))})")
    elif va ^ vb:
        soft.append(f"VARIANT WORD ON ONE SIDE ONLY ({', '.join(sorted(va ^ vb))})")
    fa, fb = A.get("forms", set()), B.get("forms", set())
    if fa and fb and not (fa & fb):
        variant.append(f"FORM DIFF ({', '.join(sorted(fa))} vs {', '.join(sorted(fb))})")
    oa = "imported" if "imported" in A["clean"] else ("local" if re.search(r"\blocal\b", A["clean"]) else "")
    ob = "imported" if "imported" in B["clean"] else ("local" if re.search(r"\blocal\b", B["clean"]) else "")
    if oa and ob and oa != ob:
        variant.append(f"ORIGIN DIFF ({oa} vs {ob})")
    hard += variant
    variant_check = "Different" if variant else "Same"
    # words that only one title has (after allowing spelling mistakes and "pop corn" = "popcorn")
    ja, jb = "".join(wa), "".join(wb)
    only_a = sorted(w for w in setA - in_b if w not in jb)
    only_b = sorted(w for w in setB - in_a if w not in ja)
    if only_a and only_b:
        soft.append(f"WORDS DIFFER ON BOTH SIDES ({', '.join(only_a[:4])} vs {', '.join(only_b[:4])})")
    elif only_a or only_b:
        info.append(f"EXTRA WORDS ON ONE SIDE ({', '.join((only_a or only_b)[:4])})")
    # price
    pa, pb = to_number(a.get("price")), to_number(b.get("price"))
    price_ratio = round(max(pa, pb) / min(pa, pb), 2) if pa and pb else None
    if price_ratio and price_ratio >= C.PRICE_GAP:
        soft.append(f"PRICE GAP x{price_ratio}")
    brand_diff = s["brand"] < C.BRAND_MIN
    if brand_diff:
        soft.append("BRAND DIFF")

    # ---------------- stage
    same_text = re.sub(r"\s+", " ", str(a["title"]).strip().lower()) == re.sub(r"\s+", " ", str(b["title"]).strip().lower())
    if same_text:
        stage = 1
    elif not hard and name_key(A) == name_key(B):
        stage = 2
    elif hard:
        stage = 6
    elif brand_diff or conf < C.MEDIUM or (only_a and only_b and conf < C.BOTH_SIDES_OK):
        stage = 5
    elif conf >= C.HIGH and not soft:
        stage = 3
    else:
        stage = 4
    return dict(stage=STAGES[stage], stage_no=stage, title_confidence=round(conf, 1),
                **{k: round(v, 1) for k, v in s.items()},
                size_check=size_check, pack_check=pack_check, variant_check=variant_check,
                price_ratio=price_ratio, checks="; ".join(hard + soft + info))


print("Helpers loaded.")


# %% ---------------------------------------------------------------- CELL 4: STAGE 1 - clean both files
def prepare(source, tab, label):
    raw = read_table(source, tab)
    print(f"{label}: {len(raw):,} rows read")
    col = find_columns(raw, label)
    df = pd.DataFrame({f: raw[c].astype(str).str.strip() for f, c in col.items()})
    for f in C.COLUMNS:
        if f not in df:
            df[f] = ""
    df["row_in_file"] = range(2, len(df) + 2)
    return df


def one_row_per_code(df):
    """Rows with the same code become one: all barcodes kept, other fields from the first filled row."""
    fields = ["title", "brand", "price", "image", "created", "category", "active"]
    d = df.copy()
    for f in fields:
        d[f] = d[f].where(~d[f].str.strip().str.lower().isin(["", "nan", "none"]))
    g = d.groupby("mpc", sort=False)
    res = g[fields].first().fillna("")
    res["row_in_file"] = g.row_in_file.first()
    res["rows_joined"] = g.size()
    bc = d[["mpc", "barcode"]].assign(b=d.barcode.map(split_barcodes)).explode("b").dropna(subset=["b"])
    bc = bc.groupby("mpc").b.agg(lambda s: sorted(set(s)))
    res["barcode"] = bc.reindex(res.index)
    res["barcode"] = res.barcode.map(lambda v: v if isinstance(v, list) else [])
    return res.reset_index()


def add_features(df):
    df["barcodes_valid"] = df.barcode.map(lambda L: [b for b in L if barcode_is_valid(b)])
    df["feat"] = df.title.map(read_attributes)
    df["title_std"] = df.feat.map(std_title)
    df["size"] = df.feat.map(lambda a: size_text(a["sizes"]))
    df["search_text"] = df.feat.map(lambda a: " ".join(sorted(a["words"])) + " " +
                                     " ".join(f"{v:g}{u}" for u, vs in a["sizes"].items() for v in vs))
    return df


def obj(r):
    return dict(title=r.title, brand=r.brand, price=r.price, feat=r.feat, std=r["title_std"])


DROPPED.clear()
t0 = time.time()
dmart = prepare(C.DMART_SOURCE, C.DMART_TAB, "Dmart")
shops_raw = prepare(C.SHOPS_SOURCE, C.SHOPS_TAB, "Shops")
dmart = add_features(one_row_per_code(dmart[(dmart.mpc != "") & (dmart.title != "")]))

drop1 = [dict(shops_code="", product_name=r.title, barcode=r.barcode, price=r.price, step="Stage 1 - Clean",
              reason=f"No product code (row {r.row_in_file})") for r in shops_raw[shops_raw.mpc == ""].itertuples()]
shops = one_row_per_code(shops_raw[shops_raw.mpc != ""])
drop1 += [dict(shops_code=r.mpc, product_name="", barcode=", ".join(r.barcode), price=r.price, step="Stage 1 - Clean",
               reason="No product name") for r in shops[shops.title == ""].itertuples()]
SHOPS_CODES_AT_START = len(shops)
shops = add_features(shops[shops.title != ""].reset_index(drop=True))
log_dropped(drop1)
print(f"Dmart products: {len(dmart):,} | Shops products: {len(shops):,} | Shops dropped (no code/name): {len(drop1):,}")
print(f"Shops products with a size in the title: {(shops['size'] != '').mean():.0%}   ({time.time()-t0:.0f}s)")


# %% ---------------------------------------------------------------- CELL 5: STAGE 2 - find possible Dmart matches
t0 = time.time()
hits = defaultdict(dict)
dmart_by_code = {c: i for i, c in enumerate(dmart.mpc)}
for i, c in enumerate(shops.mpc):
    if c in dmart_by_code:
        hits[(i, dmart_by_code[c])]["mpc"] = True
dmart_by_bc = defaultdict(list)
for j, bcs in enumerate(dmart.barcode):
    for b in bcs:
        dmart_by_bc[b].append(j)
for i, bcs in enumerate(shops.barcode):
    for b in bcs:
        for j in dmart_by_bc.get(b, [])[:5]:
            hits[(i, j)]["barcode"] = b
            hits[(i, j)]["barcode_valid"] = barcode_is_valid(b)
print("Searching the 3 closest Dmart titles for every Shops title ...")
rank = defaultdict(int)
for i, j, sim in sorted(nearest_titles(shops.search_text.tolist(), dmart.search_text.tolist(), C.TITLE_CANDIDATES),
                        key=lambda x: (x[0], -x[2])):
    rank[i] += 1
    hits[(i, j)]["text_sim"] = sim
    hits[(i, j)]["title_rank"] = rank[i]
print(f"{len(hits):,} possible pairs for {len({i for i, _ in hits}):,} Shops products   ({time.time()-t0:.0f}s)")


# %% ---------------------------------------------------------------- CELL 6: STAGE 3 - compare every pair, select one per Shops product
t0 = time.time()
rows = []
for (i, j), h in hits.items():
    s, d = shops.iloc[i], dmart.iloc[j]
    how = [k for k, on in (("MPC", h.get("mpc")), ("Barcode", h.get("barcode") and h.get("barcode_valid")),
                           ("Barcode (not valid)", h.get("barcode") and not h.get("barcode_valid")),
                           ("Title", "text_sim" in h)) if on]
    # priority: MPC (3) > valid barcode (2) > title / not-valid barcode (1)
    priority = 3 if h.get("mpc") else (2 if h.get("barcode_valid") else 1)
    rows.append(dict(shops_i=i, found_by=" + ".join(how), priority=priority,
                     shops_code=s.mpc, shops_title=s.title, dmart_code=d.mpc, dmart_title=d.title,
                     shops_size=s["size"], dmart_size=d["size"], shops_price=s.price, dmart_price=d.price,
                     shops_brand=s.brand, dmart_brand=d.brand, barcode_match=h.get("barcode", ""),
                     text_sim=h.get("text_sim"), title_rank=h.get("title_rank"),
                     shops_title_standardised=s["title_std"], dmart_title_standardised=d["title_std"],
                     **compare(obj(s), obj(d))))
P = pd.DataFrame(rows)
print(f"Compared {len(P):,} pairs ({time.time()-t0:.0f}s)")

BAD = (5, 6)        # stages that mean "not the same product"


def really_different(r):
    """Same MPC / barcode but clearly another product: size/pack/variant clash, other brand, or very low confidence."""
    return r["stage_no"] == 6 or r["title_confidence"] < C.DIFFERENT_PRODUCT_BELOW or "BRAND DIFF" in str(r["checks"])
menu, flagged_codes = [], set()
for i, g in P.groupby("shops_i", sort=True):
    g = g.sort_values(["priority", "stage_no", "title_confidence"], ascending=[False, True, False])
    flags = []
    mpc_rows, bc_rows = g[g.priority == 3], g[g.priority == 2]
    if len(mpc_rows) and len(bc_rows) and not set(mpc_rows.dmart_code) & set(bc_rows.dmart_code):
        flags.append("MPC AND BARCODE POINT TO DIFFERENT DMART PRODUCTS")
    sel = g.iloc[0]                                     # MPC beats barcode, barcode beats title
    if sel.priority == 1:
        sel = g.sort_values(["stage_no", "title_confidence"], ascending=[True, False]).iloc[0]
        if sel.stage_no in BAD:
            continue                                     # title only and not similar -> no Dmart match
        close = g[(g.stage_no == sel.stage_no) & (g.dmart_code != sel.dmart_code) &
                  (g.title_confidence >= sel.title_confidence - 2)]
        if len(close):
            flags.append(f"TWO DMART PRODUCTS EQUALLY CLOSE ({sel.dmart_code}, {close.dmart_code.iloc[0]})")
    elif really_different(sel):
        flags.append(f"SAME {'MPC' if sel.priority == 3 else 'BARCODE'} BUT DIFFERENT PRODUCT")
    # a better title match than the selected one? show it next to it
    others = g[(g.dmart_code != sel.dmart_code) & (g.stage_no < sel.stage_no) & (g.stage_no <= 3)]
    alt = others.sort_values(["stage_no", "title_confidence"], ascending=[True, False]).iloc[0] if len(others) else None
    if flags:
        flagged_codes.add(sel.shops_code)
    menu.append({**sel.to_dict(), "flags": "; ".join(flags),
                 "better_match_dmart_code": "" if alt is None else alt.dmart_code,
                 "better_match_dmart_title": "" if alt is None else alt.dmart_title,
                 "better_match_stage": "" if alt is None else alt.stage})
M = pd.DataFrame(menu)
M["shops_products_on_this_dmart"] = M.groupby("dmart_code").shops_code.transform("count")
M["Your decision"] = ""
print(M.stage.value_counts().sort_index().to_string())
print(f"Flagged: {len(flagged_codes):,}   ({time.time()-t0:.0f}s)")


# %% ---------------------------------------------------------------- CELL 7: STAGE 4 - Shops vs Shops (no Dmart match)
t0 = time.time()
matched_codes = set(M.shops_code)
alone = [i for i, c in enumerate(shops.mpc) if c not in matched_codes]
S = shops.iloc[alone].reset_index(drop=True)
print(f"Comparing {len(S):,} Shops products with no Dmart match against each other ...")
cand = {}
for a, b, sim in nearest_titles(S.search_text.tolist(), S.search_text.tolist(), C.SHOPS_CANDIDATES, same_list=True):
    cand[tuple(sorted((a, b)))] = "Title"
groups = defaultdict(list)
for i, bcs in enumerate(S.barcodes_valid):
    for b in bcs:
        groups["bc" + b].append(i)
for i, a in enumerate(S.feat):
    groups["name" + name_key(a)].append(i)
for key, idx in groups.items():
    if 1 < len(idx) <= 10:
        for a, b in itertools.combinations(sorted(idx), 2):
            cand[(a, b)] = "Barcode" if key.startswith("bc") else cand.get((a, b), "Same name")
dup = []
for (a, b), how in cand.items():
    r = compare(obj(S.iloc[a]), obj(S.iloc[b]))
    close = r["stage_no"] <= 3 or (r["stage_no"] == 4 and r["title_confidence"] >= C.HIGH)
    if close or how == "Barcode":
        dup.append(dict(stage=r["stage"], found_by=how, code_1=S.mpc[a], title_1=S.title[a], size_1=S["size"][a],
                        price_1=S.price[a], code_2=S.mpc[b], title_2=S.title[b], size_2=S["size"][b], price_2=S.price[b],
                        title_confidence=r["title_confidence"], checks=r["checks"],
                        flags="SAME BARCODE BUT DIFFERENT PRODUCT" if how == "Barcode" and really_different(r) else "",
                        **{"Your decision": ""}))
DUP = pd.DataFrame(dup, columns=["stage", "found_by", "code_1", "title_1", "size_1", "price_1", "code_2", "title_2", "size_2",
                                 "price_2", "title_confidence", "checks", "flags", "Your decision"]).sort_values(["stage", "title_confidence"], ascending=[True, False])
NOM = S[["mpc", "title", "brand", "size", "price", "category"]].rename(columns={"mpc": "shops_code"})
NOM["in_duplicate_pairs"] = NOM.shops_code.isin(set(DUP.code_1) | set(DUP.code_2))
print(f"Possible Shops duplicate pairs: {len(DUP):,}   ({time.time()-t0:.0f}s)")


# %% ---------------------------------------------------------------- CELL 8: count check + write to Google Sheets
LOG = pd.DataFrame(DROPPED, columns=["shops_code", "product_name", "barcode", "price", "step", "reason", "run_date"])
n_menu, n_nom, n_drop = len(M), len(NOM), LOG.shops_code.astype(bool).sum()
print(f"COUNT CHECK: start {SHOPS_CODES_AT_START:,} = to standard menu {n_menu:,} + no Dmart match {n_nom:,}"
      f" + dropped {n_drop:,} -> {n_menu + n_nom + n_drop:,}")
if n_menu + n_nom + n_drop != SHOPS_CODES_AT_START or len(set(M.shops_code) & set(NOM.shops_code)):
    raise SystemExit("STOP: the counts do not add up - some Shops products are missing or counted twice")

summary = pd.DataFrame(
    [("Shops products at start", SHOPS_CODES_AT_START), ("  to standard menu (a Dmart match found)", n_menu),
     ("  no Dmart match", n_nom), ("  dropped (no code / no name)", n_drop), ("Count check", "OK"), ("", "")]
    + [(f"Stage {k}", int((M.stage_no == k).sum())) for k in sorted(STAGES)]
    + [("", ""), ("Selected by MPC", int((M.priority == 3).sum())), ("Selected by barcode", int((M.priority == 2).sum())),
       ("Selected by title", int((M.priority == 1).sum())), ("", "")]
    + [(f"Flag: {f}", int(M["flags"].str.contains(f, regex=False).sum())) for f in
       ("SAME MPC BUT DIFFERENT PRODUCT", "SAME BARCODE BUT DIFFERENT PRODUCT", "MPC AND BARCODE POINT TO DIFFERENT DMART PRODUCTS",
        "TWO DMART PRODUCTS EQUALLY CLOSE")]
    + [("Possible Shops duplicate pairs (no Dmart match)", len(DUP))], columns=["Item", "Count"])
print(summary.to_string(index=False))

menu_cols = ["stage", "flags", "found_by", "shops_code", "shops_title", "dmart_code", "dmart_title", "Your decision",
             "shops_size", "dmart_size", "shops_price", "dmart_price", "price_ratio", "title_confidence",
             "levenshtein", "jaro_winkler", "token_sort", "token_set", "word_overlap", "coverage", "brand",
             "size_check", "pack_check", "variant_check", "checks", "shops_brand", "dmart_brand", "barcode_match",
             "shops_title_standardised", "dmart_title_standardised", "shops_products_on_this_dmart",
             "better_match_dmart_code", "better_match_dmart_title", "better_match_stage"]
M = M.sort_values(["stage_no", "title_confidence"], ascending=[True, False])
DECIDE = ["Same product", "Not same product", "Not sure"]
print("Writing Google Sheets ...")
write_book("Results", [("Summary", summary),
                       ("TO BE INTO STANDARD MENU", M[menu_cols], DECIDE),
                       ("Flagged", M[M["flags"] != ""][menu_cols], DECIDE),
                       ("No Dmart match", NOM),
                       ("Possible Shops duplicates", DUP, DECIDE),
                       ("Dropped products", LOG)])
pair_cols = [c for c in menu_cols if c not in ("flags", "Your decision", "shops_products_on_this_dmart", "better_match_dmart_code",
                                               "better_match_dmart_title", "better_match_stage")] + ["text_sim", "title_rank"]
write_book("All Pairs", [("All pairs", P.sort_values(["shops_code", "stage_no"])[pair_cols])])
print("\nDone. Open the links above.")
