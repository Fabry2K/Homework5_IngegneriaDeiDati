import re
from flask import Flask, render_template, request
from search import Search

app = Flask(__name__)
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

    try:
        response = search_client.search(
            index='arxiv_articles',
            query=query
        )

        hits = response['hits']['hits']
        total = response['hits']['total']['value']

    except Exception:
        hits = []
        total = 0

    return render_template(
        'index.html',
        query=query,
        results=hits,
        from_=0,
        total=total,
        es_ok=search_client.ping()
    )


@app.get('/document/<id>')
def get_document(id):
    return 'Document not found'


if __name__ == '__main__':
    app.run(debug=True)
