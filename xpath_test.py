import os
from lxml import html

# =========================
# CONFIGURAZIONE
# =========================

HTML_DIR = "arxiv_html_papers"

# 👉 CAMBIA QUESTO XPATH
XPATH_EXPR = "//span[@class='ltx_personname'] | //article[@class='ltx_document ltx_authors_1line']/div[1][@id='p1']/p[@id='p1.3']"

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

        for i, r in enumerate(results, 1):
            if hasattr(r, "text_content"):
                print(f"[{i}] {r.text_content().strip()}")
            else:
                print(f"[{i}] {str(r).strip()}")

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
