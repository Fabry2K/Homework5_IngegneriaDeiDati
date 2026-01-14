import os
from lxml import html
from urllib.parse import urljoin

# =========================
# CONFIGURAZIONE
# =========================

HTML_DIR = "arxiv_html_papers"
BASE_URL = "https://arxiv.org/html"  # base per combinare con il nome del file

# XPath corretto: prende l'intero tag <figure>
XPATH_EXPR = "//figure"

# =========================
# LOGICA
# =========================

def extract_with_xpath(html_file):
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            tree = html.parse(f)
            return tree.xpath(XPATH_EXPR)
    except Exception as e:
        return f"ERROR: {e}"

def main():
    if not os.path.isdir(HTML_DIR):
        print(f"Directory '{HTML_DIR}' non trovata.")
        return

    no_match_count = 0
    total_html = 0

    for filename in sorted(os.listdir(HTML_DIR)):
        if not filename.endswith(".html"):
            continue

        total_html += 1
        filepath = os.path.join(HTML_DIR, filename)
        results = extract_with_xpath(filepath)

        print(f"\n=== {filename} ===")

        if isinstance(results, str):
            print(results)
            no_match_count += 1
            continue

        if not results:
            print("No match")
            no_match_count += 1
            continue

        # Base URL per le immagini di questo articolo
        file_base = filename.replace(".html", "")
        article_base_url = f"{BASE_URL}/{file_base}/"

        for i, fig in enumerate(results, 1):
            # Estrazione src dell'immagine
            img_src_list = fig.xpath(".//img/@src")
            if img_src_list:
                relative_url = img_src_list[0].strip()
                img_src = urljoin(article_base_url, relative_url)  # URL completo
            else:
                img_src = "None"

            # Estrazione caption
            caption_list = fig.xpath(".//figcaption//text()")
            caption = " ".join(c.strip() for c in caption_list if c.strip())

            print(f"\n[{i}] FIGURE")
            print(f"Image URL: {img_src}")
            print(f"Caption: {caption if caption else 'None'}")

    # =========================
    # RIEPILOGO FINALE
    # =========================

    print("\n=========================")
    print(f"File HTML totali: {total_html}")
    print(f"File senza match: {no_match_count}")
    print(f"File con almeno un match: {total_html - no_match_count}")
    print("=========================")

if __name__ == "__main__":
    main()
