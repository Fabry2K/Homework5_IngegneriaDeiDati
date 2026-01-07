import os
import re
import time
import requests
import feedparser
from urllib.parse import quote_plus

# =======================
# CONFIGURAZIONE
# =======================
ARXIV_API = "http://export.arxiv.org/api/query"

KEYWORDS = [
    "automatic speech recognition",
    "speech to text"
]

BASE_DIR = "corpus/gruppo_C_asr"

RESULTS_PER_CALL = 100   # limite API arXiv
DELAY = 3                # rispetto policy arXiv

# =======================
# PREPARAZIONE CARTELLE
# =======================
os.makedirs(BASE_DIR, exist_ok=True)

# =======================
# FUNZIONI
# =======================
def sanitize_filename(text):
    """Rende sicuro il nome del file"""
    return re.sub(r"[^\w\-_.]", "_", text)

def get_html_url(entry):
    """Restituisce l'URL HTML dell'articolo se disponibile"""
    for link in entry.links:
        if link.rel == "alternate" and "/abs/" in link.href:
            return link.href.replace("/abs/", "/html/")
    return None

# =======================
# MAIN
# =======================
for keyword in KEYWORDS:
    print(f"\n🔍 Keyword: {keyword}")
    start = 0

    encoded_keyword = quote_plus(keyword)

    while True:
        query = f"all:{encoded_keyword}"

        url = (
            f"{ARXIV_API}?"
            f"search_query={query}"
            f"&start={start}"
            f"&max_results={RESULTS_PER_CALL}"
        )

        feed = feedparser.parse(url)

        # Fine risultati
        if len(feed.entries) == 0:
            break

        for entry in feed.entries:
            title = entry.title.lower()
            abstract = entry.summary.lower()

            if keyword in title or keyword in abstract:
                html_url = get_html_url(entry)
                if not html_url:
                    continue

                try:
                    response = requests.get(html_url, timeout=10)
                    if response.status_code != 200:
                        continue

                    filename = sanitize_filename(entry.title) + ".html"
                    filepath = os.path.join(BASE_DIR, filename)

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(response.text)

                    print(f"  ✔ Salvato: {entry.title}")

                except Exception:
                    continue

        start += RESULTS_PER_CALL
        time.sleep(DELAY)

print("\n Corpus ASR creato correttamente.")
