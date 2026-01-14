from query_functions import extract_dates_from_query
from query_functions import build_date_filter
from flask import Flask, render_template, request
from main import main
from search import Search

app = Flask(__name__)

main()
search_client = Search()

# Soglia minima di score per mostrare un risultato
SCORE_THRESHOLD = 0
PAGE_SIZE = 10  # risultati per pagina

@app.get('/')
def index():
    return render_template(
        'index.html',
        query='',
        results=[],
        from_=0,
        total=0,
        page_size=PAGE_SIZE,
        prev_from=None,
        next_from=None,
        es_ok=search_client.ping()
    )


@app.post('/')
def handle_search():
    page_from = request.form.get('from_', type=int, default=0)

    query = request.form.get('query', '')
    query_text, query_data = extract_dates_from_query(query)

    filters = []
    for date in query_data:
        filters.append(build_date_filter(date))

    if query_text:
        # Recupera abbastanza risultati da Elasticsearch
        es_results = search_client.search(
        query={
            "bool": {
                "should": [
                    {
                        'match' : {
                            'autori' : {
                                'query' : query_text,
                                'boost' : 6
                            }
                        }
                    },

                    {
                    'match_phrase' : {
                        'titolo' : {
                            'query' : query_text,
                            'boost' : 6
                        }
                    } 
                    }, 

                    {
                        'match' : {
                            'titolo' : {
                                'query' : query_text,
                                'boost' : 3
                            }
                        }
                    },
                ],
                'minimum_should_match' : 1,
                'filter' : filters
            }
        },
        size=20
    )

    else:

        es_results = search_client.search(
            query = {
                'bool' : {
                    'filter' : filters
                }
            }
        )


    # Filtra per score
    filtered_results = [res for res in es_results['hits']['hits'] if res['_score'] >= SCORE_THRESHOLD]
    total_filtered = len(filtered_results)

    # Pagina correttamente
    start = page_from
    end = min(page_from + PAGE_SIZE, total_filtered)
    paginated_results = filtered_results[start:end]

    # Indici per i bottoni Previous/Next
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
        next_from=next_from
    )

@app.get('/document/<id>')
def get_document(id):
    document = search_client.retrieve_document(id)
    titolo = document['_source']['titolo']
    autori = document['_source']['autori']
    data = document['_source']['data']
    abstract = document['_source']['abstract'].split('\n')
    testo = document['_source']['testo']  # lascialo come stringa HTML
    return render_template(
        'document.html',
        titolo=titolo,
        autori=autori,
        data=data,
        abstract=abstract,
        testo=testo  # renderizzato come HTML nel template
    )


if __name__ == '__main__':
    app.run(debug=True)
