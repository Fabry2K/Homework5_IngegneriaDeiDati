import re
from flask import Flask, render_template, request
from main import main
from search import Search

app = Flask(__name__)

main()
search_client = Search()

# Soglia minima di score per mostrare un risultato
SCORE_THRESHOLD = 10
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
        es_ok=search_client.ping()
    )


@app.post('/')
def handle_search():
    query = request.form.get('query', '')
    page_from = request.form.get('from_', type=int, default=0)

    # Recupera abbastanza risultati da Elasticsearch
    es_results = search_client.search(
        query={
            'bool': {
                'should': [
                    {
                        'match_phrase': {
                            'titolo': {'query': query, 'boost': 10}
                        }
                    },
                    {
                        'match': {
                            'titolo': {'query': query, 'boost': 7, 'fuzziness': 'AUTO'}
                        }
                    },
                    {
                        'match': {
                            'abstract': {'query': query, 'boost': 5, 'fuzziness': 'AUTO'}
                        }
                    }
                ]
            }
        },
        size=1000  # prendi abbastanza risultati per filtrare
    )

    # Filtra per score
    filtered_results = [res for res in es_results['hits']['hits'] if res['_score'] >= SCORE_THRESHOLD]
    total_filtered = len(filtered_results)

    # Pagina correttamente
    start = page_from
    end = min(page_from + PAGE_SIZE, total_filtered)
    paginated_results = filtered_results[start:end]

    # Indici per i bottoni Previous/Next
    prev_from = start - PAGE_SIZE if start - PAGE_SIZE >= 0 else None
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
    abstract = document['_source']['abstract']  # rimane stringa
    testo_raw = document['_source']['testo']

    # Separiamo in paragrafi solo dove ci sono due o più \n consecutivi
    paragrafi = [p.strip() for p in re.split(r'\n\s*\n', testo_raw) if p.strip()]

    return render_template(
        'document.html',
        titolo=titolo,
        autori=autori,
        data=data,
        abstract=abstract,
        testo=paragrafi
    )


if __name__ == '__main__':
    app.run(debug=True)
