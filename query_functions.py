import re
import calendar

def extract_dates_from_query(query: str):

    """
    Estrae tutte le date (yyyy, yyyy-mm, yyyy-mm-dd) dalla query
    e restituisce:
    - query_text: stringa senza le date
    - date_queries: lista di date trovate
    """

    # regex per date: yyyy, yyyy-mm, yyyy-mm-dd
    date_pattern = r'\b\d{4}(?:-\d{2})?(?:-\d{2})?\b'
    
    date_queries = re.findall(date_pattern, query)
    
    # rimuove le date dalla query originale
    query_text = re.sub(date_pattern, '', query)
    query_text = " ".join(query_text.split())  # pulisce spazi multipli

    return query_text, date_queries


def build_date_filter(query_data: str):
    """
    Costruisce un filtro range per Elasticsearch sul campo 'data'.
    Supporta:
    - anno: '2025'
    - anno-mese: '2025-03'
    - data completa: '2025-03-15'
    """

    parts = query_data.strip().split("-")

    #caso 1: input solo anno
    if len(parts)==1:
        start = f"{parts[0]}-01-01"
        end = f"{parts[0]}-12-31"
    elif len(parts)==2:
        year = int(parts[0])
        month = int(parts[1])
        last_day = calendar.monthrange(year, month)[1]
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-{last_day}" 
    else:
        start = end = query_data

    return {
        "range": {
            "data": {
                "gte": start,
                "lte": end
            }
        }
    }

def get_paperId(paper_id):

    filters = []
    
    if paper_id:
        filters.append({
            "term": {
                "paper_id": paper_id
            }
        })
    
    return filters