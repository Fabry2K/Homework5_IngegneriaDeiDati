import os
from lxml import html

# =========================
# CONFIGURAZIONE
# =========================

HTML_DIR = "arxiv_html_papers"

# =========================
# LOGICA
# =========================

def extract_tables(html_file):
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            tree = html.parse(f)

        # -------- paper_id --------
        paper_id_list = tree.xpath("//base/@href")
        paper_id = (
            paper_id_list[0].strip("/").split("/")[-1]
            if paper_id_list else "UNKNOWN"
        )

        # -------- tutte le tabelle --------
        tables = tree.xpath("//figure[contains(@class,'ltx_table')]")

        # -------- estrazione paragrafi --------
        paragraphs = tree.xpath("//p//text()")
        paragraphs = [" ".join(p.strip().split()) for p in paragraphs if p.strip()]

        return paper_id, tables, paragraphs

    except Exception as e:
        return f"ERROR: {e}", None, None


def main():
    if not os.path.isdir(HTML_DIR):
        print(f"Directory '{HTML_DIR}' non trovata.")
        return

    no_match_count = 0
    no_caption_count = 0   # contatore file senza caption
    total_html = 0

    for filename in sorted(os.listdir(HTML_DIR)):
        if not filename.endswith(".html"):
            continue

        total_html += 1
        filepath = os.path.join(HTML_DIR, filename)

        paper_id, tables, paragraphs = extract_tables(filepath)

        print(f"\n=== {filename} ===")

        if isinstance(paper_id, str) and paper_id.startswith("ERROR"):
            print(paper_id)
            no_match_count += 1
            continue

        if not tables:
            print("Nessuna tabella trovata")
            no_match_count += 1
            continue

        print(f"Paper ID: {paper_id}")

        file_has_no_caption = False  # flag per questo file

        # -------- ciclo sulle tabelle --------
        for i, table in enumerate(tables, 1):

            # table_id
            table_id = table.get("id", "NO_ID")

            # caption
            caption_list = table.xpath("./figcaption//text()")
            caption = " ".join(c.strip() for c in caption_list if c.strip())

            if not caption:
                file_has_no_caption = True  # segnalo che c'è tabella senza caption

            # body (righe)
            body_rows = table.xpath(".//tr")
            body = []
            for row in body_rows:
                cells = row.xpath(".//td//text()[not(ancestor::annotation)] | .//th//text()[not(ancestor::annotation)]")
                cells = [c.strip() for c in cells if c.strip()]
                if cells:
                    body.append(" ".join(cells))

            # -------- mentions --------
            mentions = [p for p in paragraphs if table_id in p]

            # -------- context_paragraphs --------
            keywords = set(caption.split())
            for r in body:
                keywords.update(r.split())

            context_paragraphs = [
                p for p in paragraphs if any(k in p for k in keywords)
            ]

            # -------- stampa --------
            print(f"\n[{i}] TABLE")
            print(f"Table ID: {table_id}")
            print(f"Caption: {caption if caption else 'None'}")
            print(f"Numero di righe (tr): {len(body_rows)}")
            print(f"Mentions: {len(mentions)} paragrafi")
            print(f"Context paragraphs: {len(context_paragraphs)} paragrafi")

            # opzionale: stampa contenuto delle righe
            for r, row in enumerate(body_rows, 1):
                cells = row.xpath(".//td//text()[not(ancestor::annotation)] | .//th//text()[not(ancestor::annotation)]")
                cells = [c.strip() for c in cells if c.strip()]
                print(f"  Row {r}: {cells}")

        if file_has_no_caption:
            no_caption_count += 1

    # =========================
    # RIEPILOGO FINALE
    # =========================

    print("\n=========================")
    print(f"File HTML totali: {total_html}")
    print(f"File senza tabelle: {no_match_count}")
    print(f"File con almeno una tabella senza caption: {no_caption_count}")
    print(f"File con almeno una tabella: {total_html - no_match_count}")
    print("=========================")


if __name__ == "__main__":
    main()
