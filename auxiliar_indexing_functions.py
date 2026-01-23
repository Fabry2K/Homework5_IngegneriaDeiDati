from datetime import datetime
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import re

def clean_date(data):
    data = data.replace("Generated  on ", "").replace(" by", "").strip()
    dt = datetime.strptime(data, "%a %b %d %H:%M:%S %Y")
    return dt.strftime("%Y-%m-%d")

def estrazione_autori(tree):
    raw_autori = tree.xpath("//span[@class='ltx_personname']//text()")
    autori = []
    for a in raw_autori:
        a = a.strip()
        if not a or '@' in a:
            continue
        a = re.sub(r'\[a-zA-Z]+\d', '', a)
        a = re.sub(r'\d+', '', a)
        a = re.sub(r'\s+', ' ', a).strip()
        if not a:
            continue
        parts_comma = [p.strip() for p in a.split(',') if p.strip()]
        for p in parts_comma:
            p = re.sub(r'^&+', '', p).strip()
            if re.match(r'^(and)\b', p, flags=re.IGNORECASE):
                p = re.sub(r'^(and)\b\s*', '', p, flags=re.IGNORECASE)
                if p:
                    autori.append(p)
                continue
            if re.search(r'\band\b', p, flags=re.IGNORECASE):
                parts_and = re.split(r'\band\b', p, flags=re.IGNORECASE)
                for pa in parts_and:
                    pa = pa.strip()
                    if pa:
                        autori.append(pa)
            else:
                autori.append(p)
    cleaned_autori = []
    for a in autori:
        a = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s]', '', a)
        a = re.sub(r'\s+', ' ', a).strip()
        if not a or a.lower() == "apple":
            continue
        cleaned_autori.append(a)
    return cleaned_autori

def clean_abstract(abstract):
    # Rimuove la parola "Abstract" all'inizio
    return re.sub(r'^\s*Abstract\s*', '', abstract, flags=re.IGNORECASE)





####################
######tabelle#######
####################
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



####################
######tabelle#######
####################
def estrazione_mentions(tree, keywords):

    STOP_WORDS = set(ENGLISH_STOP_WORDS)
    context_paragraphs = []

    sections = tree.xpath("//section[@class='ltx_section']")
    keywords = {k.lower() for k in keywords if k.lower() not in STOP_WORDS}

    #fisso un minimo di match per evitare falsi positivi
    min_matches = max(1, len(keywords) // 2)

    for s in sections:
        title = " ".join(s.xpath("./*[starts-with(name(), 'h')]//text()")).strip()
        paragraph = " ".join(s.xpath(".//text()")).lower()

        #tokenizzo le parole nel paragrafo (eliminando così i duplicati)
        tokens = set(re.findall(r"\b[a-zA-Z0-9\-]+\b", paragraph))

        matched = keywords & tokens
        
        if len(matched) >= min_matches:
            context_paragraphs.append(title)

    return context_paragraphs