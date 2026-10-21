"""Baseline: extract merchant details from raw card descriptors with hand-written rules.

Rules are fast, cheap, and explainable, but brittle. Run evaluate.py to see exactly
where they break, then compare with the LLM approach in extract_llm.py.
"""
import re

PROCESSORS = {r"^SQ \*": "Square", r"^TST\* ?": "Toast", r"^SP \* ?": "Shopify",
              r"^PAYPAL \*": "PayPal", r"^GOOGLE \*": "Google"}
PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
CITIES = ["ST. JOHN'S", "TORONTO", "OTTAWA", "KANATA", "MONTREAL", "VANCOUVER", "CALGARY",
          "HALIFAX", "WINNIPEG", "GUELPH", "EDMONTON", "MISSISSAUGA", "BURNABY", "SASKATOON",
          "VICTORIA", "REGINA", "LONDON", "QUEBEC", "VERDUN", "SHERBROOKE", "MARKHAM",
          "RICHMOND", "MONCTON"]
CATEGORY_KEYWORDS = {
    "Restaurants & Cafes": ["COFFEE", "BISTRO", "TIM HORTONS", "EATS", "PHO", "GRIND", "SUSHI", "DUMPLING"],
    "Groceries": ["LOBLAWS", "METRO", "COSTCO", "SOBEYS", "MARKET"],
    "Gas": ["PETRO", "ESSO"],
    "Subscriptions": ["NETFLIX", "SPOTIFY", "APPLE.COM", "YOUTUBE"],
    "Transportation": ["UBER", "PRESTO", "TRANSIT"],
    "Pharmacy": ["DRUG MART"],
    "Retail": ["CANADIAN TIRE", "WAL-MART", "DOLLARAMA", "INDIGO"],
    "Alcohol": ["LCBO", "SAQ"],
    "Utilities": ["ROGERS", "BELL", "HYDRO"],
    "Travel": ["AIR CANADA", "VIA RAIL", "AIRBNB"],
    "Online Shopping": ["AMZN"],
    "Personal Care": ["BARBER", "SALON", "SPA"],
    "Entertainment": ["CINEPLEX", "CINEMA", "THEATRE"],
}
# Shopify mostly powers online stores, so use it as a fallback when no keyword matches.
PROCESSOR_CATEGORIES = {"Shopify": "Online Shopping"}
# Brands whose descriptor can't be cleaned by general rules (spelling, abbreviations).
MERCHANT_ALIASES = {"WAL-MART": "Walmart", "AMZN MKTP": "Amazon Marketplace",
                    "UBER* EATS": "Uber Eats", "UBER* TRIP": "Uber"}
# Words that describe the payment or the network, not the merchant.
NOISE = re.compile(r"\b(PRESTO|ONLINE PMT|BILL PAYMENT|SELECTION)\b")
ACRONYMS = {"LCBO", "SAQ", "OC", "GO", "VIA", "CN", "IGA"}
URL = r"\S+\.(COM|CA|CO|NET|ORG)\b\S*"


def extract(raw: str) -> dict:
    text = raw.upper().strip()
    out = {"merchant": "", "processor": "", "city": "", "province": "", "category": ""}

    for pattern, name in PROCESSORS.items():
        if re.match(pattern, text):
            out["processor"] = name
            text = re.sub(pattern, "", text).strip()
            break

    tokens = text.split()
    if tokens and tokens[-1] == "CA":  # country code, not a province
        tokens = tokens[:-1]
        text = " ".join(tokens)
    if tokens and tokens[-1] in PROVINCES:
        out["province"] = tokens[-1]
        text = " ".join(tokens[:-1])
    for city in CITIES:
        if text.endswith(" " + city):
            out["city"] = city.title().replace("'S", "'s")
            text = text[: -len(city)].strip()
            break

    for cat, words in CATEGORY_KEYWORDS.items():
        # Whole words only, so "BELL" doesn't match "LA BELLE PROVINCE".
        if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", raw.upper()) for w in words):
            out["category"] = cat
            break
    if not out["category"]:
        out["category"] = PROCESSOR_CATEGORIES.get(out["processor"], "")

    for prefix, name in MERCHANT_ALIASES.items():
        if text.startswith(prefix):
            out["merchant"] = name
            return out

    # A descriptor that starts with a domain (NETFLIX.COM, APPLE.COM/BILL) names the brand.
    domain = re.match(URL, text)
    if domain:
        out["merchant"] = domain.group(0).split(".")[0].title()
        return out

    # Strip URLs, store numbers (#123, W532, STALL 12), phone numbers, reference codes,
    # "/SUFFIX" sub-brands and payment noise words.
    text = re.sub(URL, " ", text)
    text = re.sub(r"#\s?\S+|\b[A-Z]\d{3,}\b|(?<=STALL) \d+\b|\b\d[\d-]{2,}\b|\*\S+|/\S+",
                  " ", text)
    text = NOISE.sub(" ", text)
    words = re.sub(r"\s+", " ", text).strip(" -*/").split()
    out["merchant"] = " ".join(w if w in ACRONYMS else w.title() for w in words)
    return out


if __name__ == "__main__":
    for example in ["SQ *JOES COFFEE TORONTO ON", "TIM HORTONS #3421 KANATA ON"]:
        print(example, "->", extract(example))
