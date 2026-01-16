import os
import time
import re

from auxiliar_indexing_functions import estrazione_context_paragraphs
from lxml import html
from urllib.parse import urljoin
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class TablesSearch:
    def __init__(self):
        self.es = Elasticsearch(
            os.getenv('ELASTIC_URL', 'http://localhost:9200'), verify_certs=False
        )
        self.index_name = 'hwk5_tables'
        print('Connected to Elasticsearch (Figures)!')

    def ping(self):
        return self.es.ping()

    ############################
    #### Creazione indice #####
    ############################

    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name, body={
            'mappings': {
                'properties': {
                    'paper_id': {'type': 'text'},
                    'table_id': {'type': 'text'},
                    'caption': {'type': 'text'},
                    'body': {'type': 'text'},
                    'mentionts' : {'type' : 'text'},
                    'context_paragraph' : {'type' : 'text'}
                }
            }
        })

    ############################
    #### Indicizzazione #######
    ############################

    def docs(self):
        conversion_start = time.time()
        documents = []

        html_path = os.path.join('.', 'arxiv_html_papers')
        for file in os.listdir(html_path):
            if not file.endswith('.html'):
                continue

            full_path = os.path.join(html_path, file)
            with open(full_path, 'r', encoding='utf-8') as f:
                tree = html.fromstring(f.read())

                tables = tree.xpath("//figure[contains(@class='ltx_table')]")

                #Id paper-univoco
                paper_id = tree.xpath("//base/@href")[0].strip("/").split("/")[-1]

                for t in tables:

                    table_id = t.get("id", "NO_ID")

                    caption = t.xpath("./figcaption//text()")
                    caption = " ".join(c.strip() for c in caption if c.strip())
                    
                    keywords = set(caption.split())
              
                    body_rows = t.xpath(".//tr")
                    body = []

                    for row in body_rows:
                        column = row.xpath(".//td//text()[not(ancestor::annotation)] | .//th//text()[not(ancestor::annotation)]")
                        column = " ".join(c.strip() for c in column if c.strip())
                        if column:
                            body.append(column)

                        keywords.update(row.split())
                    

                    context_paragraphs = estrazione_context_paragraphs(tree, keywords)
                    
                    documents.append({
                        '_index': self.index_name,
                        '_source': {
                            'paper_id' : paper_id,
                            'table_id' : table_id,
                            'caption' : caption,
                            'body' : body
                        }
                    })

        conversion_end = time.time()
        print(f'Tables conversion time: {conversion_end - conversion_start:.3f}s')
        return documents

    def insert_documents(self):
        documents = self.docs()
        for doc in documents:
            self.es.index(index=self.index_name, body=doc['_source'])
        print('Figures indexed successfully')

    ############################
    #### Query ################
    ############################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)
