import os
import time
from lxml import html
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

from auxiliar_indexing_functions import clean_date
from auxiliar_indexing_functions import clean_abstract
from auxiliar_indexing_functions import estrazione_autori

load_dotenv()


class Search:
    def __init__(self):
        self.es = Elasticsearch(
            os.getenv('ELASTIC_URL', 'http://localhost:9200'),
            verify_certs=False
        )
        self.index_name = 'hwk5_dataing'

    def ping(self):
        return self.es.ping()

    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name, body={
            'mappings': {
                'properties': {
                    'titolo': {'type': 'text'},
                    'abstract': {'type': 'text'},
                    'data': {'type': 'date', 'format': 'yyyy-MM-dd'},
                    'autori': {'type': 'text'},
                    'testo': {'type': 'text'}
                }
            }
        })

    def docs(self):
        documents = []
        html_path = os.path.join('.', 'arxiv_html_papers')

        for file in os.listdir(html_path):
            if not file.endswith('.html'):
                continue

            full_path = os.path.join(html_path, file)
            with open(full_path, 'r', encoding='utf-8') as f:
                tree = html.fromstring(f.read())

                titolo = tree.xpath("//h1[@class='ltx_title ltx_title_document']/text()")
                abstract = tree.xpath("//div[@class='ltx_abstract']//text()")
                data = tree.xpath("//div[@class='ltx_page_logo']/text()")
                autori = estrazione_autori(tree)

                sections = tree.xpath("//section[@class='ltx_section']")
                testo_blocks = []
                for sec in sections:
                    for note in sec.xpath('.//span[contains(@class,"ltx_note")]'):
                        note.getparent().remove(note)
                    testo_blocks.append(html.tostring(sec, encoding='unicode', method='html'))
                testo = "\n".join(testo_blocks)

                titolo = " ".join(t.strip() for t in titolo if t.strip())
                abstract = clean_abstract(" ".join(a.strip() for a in abstract if a.strip()))
                data = clean_date(" ".join(d.strip() for d in data if d.strip()))

                documents.append({
                    '_index': self.index_name,
                    '_source': {
                        'titolo': titolo,
                        'abstract': abstract,
                        'data': data,
                        'autori': autori,
                        'testo': testo
                    }
                })

        return documents

    def insert_documents(self):
        documents = self.docs()
        for doc in documents:
            self.es.index(index=self.index_name, body=doc['_source'])

        print(f"[ARTICLES] Indicizzati {len(documents)} articoli")

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)

    def retrieve_document(self, id):
        return self.es.get(index=self.index_name, id=id)
