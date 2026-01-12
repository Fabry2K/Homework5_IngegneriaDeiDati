import re
from flask import Flask, render_template, request
from main import main
from search import Search

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
                    'should' :[
                        {
                            'match_phrase' : {
                                'titolo' : {            # --> greeter correspondence, greeter score
                                    'query' : query,
                                    'boost' : 10
                                }
                            }
                        },
                        {
                            'match' : {
                                'titolo' : {             # --> if title's tokens matche score = 7
                                    'query' : query,
                                    'boost' : 7,
                                    'fuzziness': 'AUTO'
                                }
                            }
                        },
                        {
                            'match' : {
                                'abstract' : {           # --> if content's tokens mathch score = 5
                                    'query' : query,
                                    'boost' : 5,
                                    'fuzziness': 'AUTO'
                                }
                            }
                        }
                    ]
        
                }
            }, size=10, from_=from_
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
    titolo = document['_source']['titolo']
    abstract = document['_source']['abstract'].split('\n')
    return render_template('document.html', titolo=titolo, abstract=abstract)


if __name__ == '__main__':
    app.run(debug=True)
