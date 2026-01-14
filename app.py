from flask import Flask, render_template, request
from main import main
from search import Search
from figures_search import FigureSearch
from query_functions import extract_dates_from_query, build_date_filter

app = Flask(__name__)

# =========================
# Inizializzazione
# =========================

main()
search_client = Search()

figure_client = FigureSearch()
figure_client.insert_documents()

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
    page_from = request.form.get('from_', type=int, default=0)
    index_type = request.form.get('index_type', 'articles')

    # =========================
    # SEARCH ARTICOLI
    # =========================
    if index_type == 'articles':
        query_text, query_dates = extract_dates_from_query(query)

        filters = []
        for date in query_dates:
            filters.append(build_date_filter(date))

        if query_text:
            es_results = search_client.search(
                query={
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "autori": {
                                        "query": query_text,
                                        "boost": 6
                                    }
                                }
                            },
                            {
                                "match_phrase": {
                                    "titolo": {
                                        "query": query_text,
                                        "boost": 6
                                    }
                                }
                            },
                            {
                                "match": {
                                    "titolo": {
                                        "query": query_text,
                                        "boost": 3
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1,
                        "filter": filters
                    }
                },
                size=1000
            )
        else:
            es_results = search_client.search(
                query={
                    "bool": {
                        "filter": filters
                    }
                },
                size=1000
            )

    # =========================
    # SEARCH FIGURE
    # =========================
    else:
        es_results = figure_client.search(
            query={
                'bool': {
                    'should': [
                        {
                            'match_phrase': {
                                'caption': {
                                    'query': query,
                                    'boost': 10
                                }
                            }
                        },
                        {
                            'match': {
                                'caption': {
                                    'query': query,
                                    'boost': 7,
                                    'fuzziness': 'AUTO'
                                }
                            }
                        },
                        {
                            'match': {
                                'citing_paragraphs': {
                                    'query': query,
                                    'boost': 5
                                }
                            }
                        },
                        {
                            'match': {
                                'semantic_context': {
                                    'query': query,
                                    'boost': 5
                                }
                            }
                        }
                    ]
                }
            },
            size=1000
        )

    # =========================
    # POST-PROCESSING
    # =========================

    filtered_results = [
        res for res in es_results['hits']['hits']
        if res['_score'] >= SCORE_THRESHOLD
    ]

    total_filtered = len(filtered_results)

    start = page_from
    end = min(page_from + PAGE_SIZE, total_filtered)
    paginated_results = filtered_results[start:end]

    prev_from = start - PAGE_SIZE if start > 0 else None
    next_from = end if end < total_filtered else None

    return render_template(
        'index.html',
        results=paginated_results,
        query=query,
        from_=start,
        total=total_filtered,
        page_size=PAGE_SIZE,
        prev_from=prev_from,
        next_from=next_from,
        index_type=index_type
    )

# =========================
# DOCUMENT VIEW
# =========================

@app.get('/document/<id>')
def get_document(id):
    document = search_client.retrieve_document(id)

    return render_template(
        'document.html',
        titolo=document['_source']['titolo'],
        autori=document['_source']['autori'],
        data=document['_source']['data'],
        abstract=document['_source']['abstract'].split('\n'),
        testo=document['_source']['testo']
    )

# =========================
# FIGURE VIEW
# =========================

@app.get('/figure/<id>')
def get_figure(id):
    document = figure_client.es.get(
        index=figure_client.index_name,
        id=id
    )

    return render_template(
        'figure.html',
        url=document['_source']['url'],
        caption=document['_source']['caption'],
        citing_paragraphs=document['_source'].get('citing_paragraphs', []),
        semantic_context=document['_source'].get('semantic_context', [])
    )

# =========================
# RUN
# =========================

if __name__ == '__main__':
    app.run(debug=True)
