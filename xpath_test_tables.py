import os
import re
from lxml import html
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

HTML_DIR = "arxiv_html_papers"

# =========================
# FUNZIONI
# =========================

def estrazione_context_paragraphs(tree, keywords):

    STOP_WORDS = set(ENGLISH_STOP_WORDS)
    context_paragraphs = []

    section = tree.xpath("//section[@class='ltx_section']")
    appendix = tree.xpath("//section[@class='ltx_appendix']")

    keywords = {k.lower() for k in keywords if k.lower() not in STOP_WORDS}

    #fisso un minimo di match per evitare falsi positivi
    min_matches = max(1, len(keywords) // 2)

    for s in section:

        #prima analisi della sezione
        section_title = " ".join(s.xpath("./*[starts-with(name(), 'h')]//text()")).strip()
        section_text = " ".join(s.xpath("./*[not(self::section)]//text()")).lower()

        #tokenizzo le parole nel paragrafo (eliminando così i duplicati)
        section_tokens = set(re.findall(r"\b[a-zA-Z0-9\-]+\b", section_text))

        matched = keywords & section_tokens

        if len(matched)>=min_matches:
            context_paragraphs.append(section_title)

        #ora si analizzano i paragrafi di sezione (se ci sono)
        paragraphs = s.xpath("./section")

        if paragraphs:
            for p in paragraphs:
                paragraph_title = " ".join(p.xpath("./*[starts-with(name(), 'h')]//text()")).strip()
                paragraph_text = " ".join(p.xpath(".//text()")).lower()

                #tokenizzo le parole nel paragrafo (eliminando così i duplicati)
                paragraph_tokens = set(re.findall(r"\b[a-zA-Z0-9\-]+\b", paragraph_text))

                matched = keywords & paragraph_tokens

                if len(matched)>=min_matches:
                    context_paragraphs.append(paragraph_title)

    if appendix:
        for a in appendix:
            app_title = " ".join(a.xpath("./*[starts-with(name(), 'h')][1]//text()")).strip()
            app_text = " ".join(a.xpath(".//text()")).lower()

            #tokenizzo le parole nel paragrafo (eliminando così i duplicati)
            app_tokens = set(re.findall(r"\b[a-zA-Z0-9\-]+\b", app_text))

            matched = keywords & app_tokens
        
            if len(matched)>=min_matches:
                context_paragraphs.append(app_title)

    return context_paragraphs


def extract_tables(html_file):
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            tree = html.parse(f)

        paper_id_list = tree.xpath("//base/@href")
        paper_id = (
            paper_id_list[0].strip("/").split("/")[-1]
            if paper_id_list else "UNKNOWN"
        )

        tables = tree.xpath("//figure[contains(@class,'ltx_table')]")

        return paper_id, tables, tree

    except Exception as e:
        return f"ERROR: {e}", None, None


# =========================
# MAIN
# =========================

def main():
    if not os.path.isdir(HTML_DIR):
        print(f"Directory '{HTML_DIR}' non trovata.")
        return

    for filename in sorted(os.listdir(HTML_DIR)):
        if not filename.endswith(".html"):
            continue

        filepath = os.path.join(HTML_DIR, filename)
        paper_id, tables, tree = extract_tables(filepath)

        print(f"\n=== {filename} ===")

        if not tables:
            print("Nessuna tabella trovata")
            continue

        subsections_count = len(tree.xpath("//section[@class='ltx_subsection']"))
        print(f"Numero di sottosezioni: {subsections_count}")

        print(f"Paper ID: {paper_id}")

        for i, t in enumerate(tables, 1):

            table_id = t.get("id", "NO_ID")

            caption_list = t.xpath("./figcaption//text()")
            caption = " ".join(c.strip() for c in caption_list if c.strip())

            keywords = set(caption.split())

            context_sections = estrazione_context_paragraphs(tree, keywords)

            print(f"\n[{i}] TABLE")
            print(f"Table ID: {table_id}")
            print(f"Caption: {caption if caption else 'None'}")
            print(f"Context sections: {len(context_sections)}")

            for title in context_sections:
                print(f"  - {title}")


if __name__ == "__main__":
    main()
