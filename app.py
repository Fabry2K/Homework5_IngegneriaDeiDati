from flask import Flask, render_template, request
from search import Search
from figures_search import FigureSearch
from tables_search import TablesSearch
from query_functions import extract_dates_from_query, build_date_filter
from query_functions import get_paperId

app = Flask(__name__)

# =========================
# Clients
# =========================

search_client = Search()
figure_client = FigureSearch()
table_client = TablesSearch()

SCORE_THRESHOLD = 0
PAGE_SIZE = 10

# =========================
# HOME
# =========================

@app.get('/')
def index():
    index_type = request.args.get('index_type', 'articles')

    return render_template(
        'index.html',
        query='',
        results=[],
        from_=0,
        total=0,
        page_size=PAGE_SIZE,
        prev_from=None,
        next_from=None,
        es_ok=search_client.ping(),
        index_type=index_type
    )

# =========================
# SEARCH
# =========================

@app.post('/')
def handle_search():
    query = request.form.get('query', '')
    paper_id = request.form.get("paper_id", "").strip()
    paperId_filter = get_paperId(paper_id)

    page_from = request.form.get('from_', type=int, default=0)
    index_type = request.form.get('index_type', 'articles')

    # ========= ARTICLES =========
    if index_type == 'articles':
        query_text, query_dates = extract_dates_from_query(query)
        filters = [build_date_filter(d) for d in query_dates]

        if query_text:
            es_results = search_client.search(
                query={
                    "bool": {
                        "should": [
                            {"match": {"autori": {"query": query_text, "boost": 6, "fuzziness": "AUTO"}}},
                            {"match_phrase": {"titolo": {"query": query_text, "boost": 6}}},
                            {"match": {"titolo": {"query": query_text, "boost": 3, "fuzziness": "AUTO"}}}
                        ],
                        "filter": filters
                    }
                },
                size=1000
            )
        if query_dates:
            es_results = search_client.search(
                query={"bool": {"must": {"match_all": {}}, "filter": filters}},
                size=1000
            )
        else:
            es_results = {"hits": {"hits": []}}

    # ========= FIGURES =========
    elif index_type == 'figures':
        es_results = figure_client.search(
            query={
                "bool": {
                    "should": [
                        {"match_phrase": {"caption": {"query": query, "boost": 10}}},
                        {"match": {"caption": {"query": query, "boost": 7, "fuzziness": "AUTO"}}}
                    ],
                    "filter": paperId_filter
                }
            },
            size=1000
        )

    # ========= TABLES =========
    else:
        es_results = table_client.search(
            query={
                "bool": {
                    "should": [
                        {"match_phrase": {"caption": {"query": query, "boost": 10}}},
                        {"match": {"caption": {"query": query, "boost": 7, "fuzziness": "AUTO"}}},
                        {"match": {"mentions": {"query": query, "boost": 7}}},
                        {"match": {"context_paragraphs": {"query": query, "boost": 5}}}
                    ],
                    "filter": paperId_filter
                }
            },
            size=1000
        )

    filtered_results = [
        r for r in es_results['hits']['hits']
        if r['_score'] >= SCORE_THRESHOLD
    ]

    total = len(filtered_results)
    start = page_from
    end = min(start + PAGE_SIZE, total)

    return render_template(
        'index.html',
        results=filtered_results[start:end],
        query=query,
        from_=start,
        total=total,
        page_size=PAGE_SIZE,
        prev_from=start - PAGE_SIZE if start > 0 else None,
        next_from=end if end < total else None,
        index_type=index_type,
        paper_id=paper_id
    )

# =========================
# DOCUMENT VIEW (ARTICLES)
# =========================

@app.get('/document/<id>')
def get_document(id):
    doc = search_client.retrieve_document(id)

    return render_template(
        'document.html',
        titolo=doc['_source']['titolo'],
        autori=doc['_source']['autori'],
        data=doc['_source']['data'],
        abstract=doc['_source']['abstract'].split('\n'),
        testo=doc['_source']['testo']
    )

# =========================
# FIGURE VIEW
# =========================

@app.get('/figure/<id>')
def get_figure(id):
    doc = figure_client.es.get(
        index=figure_client.index_name,
        id=id
    )['_source']

    figure = {
        "figure_id": id,
        "paper_id": doc.get("paper_id"),
        "url": doc.get("url"),
        "caption": doc.get("caption", ""),
        "citing_paragraphs": doc.get("citing_paragraphs", [])
    }

    return render_template(
        'figure.html',
        figure=figure
    )

# =========================
# TABLE VIEW
# =========================

@app.get('/table/<id>')
def get_table(id):
    response = table_client.es.get(
        index=table_client.index_name,
        id=id
    )

    doc = response['_source']

    table = {
        "table_id": id,
        "paper_id": doc.get("paper_id"),
        "caption": doc.get("caption", ""),
        "table_html": doc.get("table_html", ""),
        "mentions": doc.get("mentions", []),
        "context_paragraphs": doc.get("context_paragraphs", [])
    }

    return render_template(
        'table.html',
        table=table
    )

# =========================
# MAIN
# =========================

if __name__ == '__main__':
    app.run(debug=True)
