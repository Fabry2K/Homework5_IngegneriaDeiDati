import os
import time
from lxml import html
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

from auxiliar_indexing_functions import estrazione_context_paragraphs
from auxiliar_indexing_functions import estrazione_mentions

load_dotenv()


class TablesSearch:
    def __init__(self):
        self.es = Elasticsearch(
            os.getenv('ELASTIC_URL', 'http://localhost:9200'),
            verify_certs=False
        )
        self.index_name = 'hwk5_tables'

    def ping(self):
        return self.es.ping()

    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name, body={
            'mappings': {
                'properties': {
                    'paper_id': {'type': 'keyword'},
                    'table_id': {'type': 'keyword'},
                    'caption': {'type': 'text'},
                    'body': {'type': 'text'},
                    'mentions': {'type': 'text'},
                    'context_paragraphs': {'type': 'text'}
                }
            }
        })

    def docs(self):
        documents = []
        keyword_counts = []

        html_path = os.path.join('.', 'arxiv_html_papers')

        for file in os.listdir(html_path):
            if not file.endswith('.html'):
                continue

            full_path = os.path.join(html_path, file)
            with open(full_path, 'r', encoding='utf-8') as f:
                tree = html.fromstring(f.read())
                tables = tree.xpath("//figure[contains(@class, 'ltx_table')]")

                base_hrefs = tree.xpath("//base/@href")
                paper_id = base_hrefs[0].strip("/").split("/")[-1] if base_hrefs else file.replace('.html', '')

                for t in tables:
                    table_id = t.get("id", "NO_ID")
                    caption = " ".join(c.strip() for c in t.xpath("./figcaption//text()") if c.strip())

                    keywords = set(caption.split())
                    body = []

                    for row in t.xpath(".//tr"):
                        cells = row.xpath(".//td//text() | .//th//text()")
                        text = " ".join(c.strip() for c in cells if c.strip())
                        if text:
                            body.append(text)
                            keywords.update(text.split())

                    context_paragraphs = estrazione_context_paragraphs(tree, keywords)
                    mentions = estrazione_mentions(tree, table_id)

                    context_paragraphs = list(dict.fromkeys(p for p in context_paragraphs if p.strip()))
                    mentions = list(dict.fromkeys(m for m in mentions if m.strip()))

                    keyword_counts.append(len(keywords))

                    documents.append({
                        '_index': self.index_name,
                        '_source': {
                            'paper_id': paper_id,
                            'table_id': table_id,
                            'caption': caption,
                            'body': body,
                            'mentions': mentions,
                            'context_paragraphs': context_paragraphs
                        }
                    })

        return documents, keyword_counts

    def insert_documents(self):
        documents, keyword_counts = self.docs()

        for doc in documents:
            self.es.index(index=self.index_name, body=doc['_source'])

        avg_keywords = (
            sum(keyword_counts) / len(keyword_counts)
            if keyword_counts else 0
        )

        print(
            f"[TABLES] Indicizzate {len(documents)} tabelle | "
            f"Keyword medie per tabella: {avg_keywords:.2f}"
        )

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)
