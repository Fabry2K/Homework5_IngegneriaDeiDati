from flask import Flask, render_template, request
from search import Search
from main import main

app = Flask(__name__)
main()
search_client = Search()


@app.get('/')
def index():
    return render_template(
        'index.html',
        query='',
        results=[],
        from_=0,
        total=0,
        es_ok=search_client.ping()
    )


@app.post('/')
def handle_search():
    query = request.form.get('query', '')
    from_ = request.form.get('from_', type=int, default=0)

    results = search_client.search(
        query={
            'bool': {
                'should': [
                    {
                        'match_phrase': {
                            'titolo': {
                                'query': query,
                                'boost': 10
                            }
                        }
                    },
                    {
                        'match': {
                            'titolo': {
                                'query': query,
                                'boost': 7,
                                'fuzziness': 'AUTO'
                            }
                        }
                    },
                    {
                        'match': {
                            'abstract': {
                                'query': query,
                                'boost': 5,
                                'fuzziness': 'AUTO'
                            }
                        }
                    }
                ],
                'minimum_should_match': 1
            }
        },
        size=5,
        from_=from_
    )

    return render_template(
        'index.html',
        results=results['hits']['hits'],
        query=query,
        from_=from_,
        total=results['hits']['total']['value']
    )


@app.get('/document/<id>')
def get_document(id):
    
    document = search_client.retrieve_document(id)
    source = document['_source']

    return render_template(
        'document.html',
        titolo=source.get('titolo', ''),
        autori=", ".join(source.get('autori', [])),
        data=source.get('data', ''),
        abstract=source.get('abstract', ''),
        testo=source.get('testo', '')
    )


if __name__ == '__main__':
    app.run(debug=True)
