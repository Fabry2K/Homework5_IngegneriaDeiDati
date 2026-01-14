from datetime import datetime
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
