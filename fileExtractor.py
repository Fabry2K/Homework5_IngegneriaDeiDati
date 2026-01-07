import requests
import feedparser
import time
import os

ARXIV_API_URL = "http://export.arxiv.org/api/query"

KEYWORDS = [
    "automatic speech recognition",
    "speech to text"
]

RESULTS_PER_PAGE = 100
MAX_RESULTS = 500
OUTPUT_DIR = "arxiv_html_papers"


def build_query():
    return " OR ".join(f'all:"{kw}"' for kw in KEYWORDS)


def extract_arxiv_id(entry_id):
    # esempio: http://arxiv.org/abs/2301.12345v2
    return entry_id.split("/")[-1]


def html_url(arxiv_id):
    return f"https://arxiv.org/html/{arxiv_id}"


def download_html(arxiv_id):
    url = html_url(arxiv_id)
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and "<html" in r.text.lower():
            return r.text
    except requests.RequestException:
        pass
    return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    query = build_query()
    start = 0
    saved = 0

    while start < MAX_RESULTS:
        params = {
            "search_query": query,
            "start": start,
            "max_results": RESULTS_PER_PAGE
        }

        response = requests.get(ARXIV_API_URL, params=params)
        feed = feedparser.parse(response.text)

        if not feed.entries:
            break

        for entry in feed.entries:
            arxiv_id = extract_arxiv_id(entry.id)
            print(f"Controllo {arxiv_id}...")

            html = download_html(arxiv_id)
            if html:
                filename = arxiv_id.replace("/", "_") + ".html"
                path = os.path.join(OUTPUT_DIR, filename)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(html)

                print(f"  ✔ Salvato: {path}")
                saved += 1

            time.sleep(0.5)  # rispetto dei rate limit

        start += RESULTS_PER_PAGE

    print(f"\nTotale articoli HTML salvati: {saved}")


if __name__ == "__main__":
    main()
