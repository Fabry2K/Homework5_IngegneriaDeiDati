import requests
import feedparser
import time
import os
import re

ARXIV_API_URL = "http://export.arxiv.org/api/query"

OUTPUT_DIR = "arxiv_html_papers"
RESULTS_PER_PAGE = 100
MAX_RESULTS = 2000   # limite API arXiv
API_DELAY = 3        # secondi tra chiamate API
HTML_DELAY = 2       # secondi tra download HTML


# Token richiesti (matching parziale)
TOKEN_GROUPS = [
    {"automatic", "speech", "recognition"},
    {"speech", "text"}
]


def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text


def matches_partial(title, abstract):
    text = normalize(title + " " + abstract)
    tokens = set(text.split())

    for group in TOKEN_GROUPS:
        if group.issubset(tokens):
            return True
    return False


def extract_arxiv_id(entry_id):
    return entry_id.split("/")[-1]


def download_html(arxiv_id):
    url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and "<html" in r.text.lower():
            return r.text
    except requests.RequestException:
        pass
    return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start = 0
    saved = 0

    # Query API *larga* (solo per recuperare candidati)
    search_query = "ti:speech OR abs:speech"

    while start < MAX_RESULTS:
        print(f"\nRichiesta API: start={start}")

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": RESULTS_PER_PAGE
        }

        response = requests.get(ARXIV_API_URL, params=params)
        feed = feedparser.parse(response.text)

        if not feed.entries:
            break

        for entry in feed.entries:
            title = entry.title
            abstract = entry.summary

            if not matches_partial(title, abstract):
                continue

            arxiv_id = extract_arxiv_id(entry.id)
            print(f"  Match testuale: {arxiv_id}")

            html = download_html(arxiv_id)
            if html:
                filename = arxiv_id.replace("/", "_") + ".html"
                path = os.path.join(OUTPUT_DIR, filename)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)

                saved += 1
                print(f"    ✔ HTML salvato")

                time.sleep(HTML_DELAY)

        start += RESULTS_PER_PAGE
        time.sleep(API_DELAY)

    print(f"\nTotale articoli HTML salvati: {saved}")


if __name__ == "__main__":
    main()
