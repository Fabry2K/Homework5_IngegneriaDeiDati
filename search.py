import json
from pprint import pprint
from datetime import datetime
import os
import time
import re

from lxml import html
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class Search:
    def __init__(self):
        # Legacy client, nessuna password/username
        self.es = Elasticsearch(os.getenv('ELASTIC_URL', 'http://localhost:9200'), verify_certs=False)
        self.index_name = 'hwk5_dataing'
        print('Connected to Elasticsearch!')

    def ping(self):
        return self.es.ping()

    ###################################
    ####### Creazione dell'indice #####
    ###################################

    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name, body={
            'mappings': {
                'properties': {
                    'titolo': {'type': 'text'},
                    'abstract': {'type': 'text'},
                    'data': {"type": "date", "format": "yyyy-MM-dd"},
                    'autori': {'type': 'text'},
                    'testo': {'type': 'text'}
                }
            }
        })

    ###################################
    # Inserimento documenti nell'indice #
    ###################################

    def docs(self):
        conversion_start = time.time()
        documents = []

        textfiles_path = os.path.join('.', 'arxiv_html_papers')
        for file in os.listdir(textfiles_path):
            if file.endswith('.html'):
                full_path = os.path.join(textfiles_path, file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                    tree = html.fromstring(html_content)

                    # XPath
                    titolo = tree.xpath("//h1[@class='ltx_title ltx_title_document']/text()")    
                    abstract = tree.xpath("//div[@class='ltx_abstract']//text()")                 
                    data = tree.xpath("//div[@class='ltx_page_logo']/text()")                  
                    autori = self.estrazione_autori(tree)  
                    testo = tree.xpath("//section[@class='ltx_section']")[0].xpath('string(.)') if tree.xpath("//section[@class='ltx_section']") else ''

                    # Pulizia
                    titolo = " ".join(t.strip() for t in titolo if t.strip())
                    abstract = " ".join(a.strip() for a in abstract if a.strip())
                    abstract = self.clean_abstract(abstract)
                    data = " ".join(d.strip() for d in data if d.strip())               
                    data = self.clean_date(data)
                    testo = testo.strip()

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

        conversion_end = time.time()
        print(f'Conversion Time: {conversion_end - conversion_start:.3f}s')
        return documents

    def insert_documents(self):
        index_start = time.time()
        documents = self.docs()
        for document in documents:
            self.es.index(index=self.index_name, body=document['_source'])
        print('Inserted successfully')

    ####################
    # Funzioni ausiliarie #
    ####################

    def clean_date(self, data):
        data = data.replace("Generated  on ", "").replace(" by", "").strip()
        dt = datetime.strptime(data, "%a %b %d %H:%M:%S %Y")
        return dt.strftime("%Y-%m-%d")

    def estrazione_autori(self, tree):
        raw_autori = tree.xpath("//span[@class='ltx_personname']//text()")
        autori = []
        for a in raw_autori:
            a = a.strip()
            if not a or '@' in a:
                continue
            a = re.sub(r'\[a-zA-Z]+\d', '', a)
            a = re.sub(r'\d+', '', a)
            a = re.sub(r'\s+', ' ', a).strip()
            if not a:
                continue
            parts_comma = [p.strip() for p in a.split(',') if p.strip()]
            for p in parts_comma:
                p = re.sub(r'^&+', '', p).strip()
                if re.match(r'^(and)\b', p, flags=re.IGNORECASE):
                    p = re.sub(r'^(and)\b\s*', '', p, flags=re.IGNORECASE)
                    if p:
                        autori.append(p)
                    continue
                if re.search(r'\band\b', p, flags=re.IGNORECASE):
                    parts_and = re.split(r'\band\b', p, flags=re.IGNORECASE)
                    for pa in parts_and:
                        pa = pa.strip()
                        if pa:
                            autori.append(pa)
                else:
                    autori.append(p)
        cleaned_autori = []
        for a in autori:
            a = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s]', '', a)
            a = re.sub(r'\s+', ' ', a).strip()
            if not a or a.lower() == "apple":
                continue
            cleaned_autori.append(a)
        return cleaned_autori

    def clean_abstract(self, abstract):
        # Rimuove la parola "Abstract" all'inizio
        return re.sub(r'^\s*Abstract\s*', '', abstract, flags=re.IGNORECASE)

    ###################
    ####### Query #######
    ###################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)

    def retrieve_document(self, id):
        return self.es.get(index=self.index_name, id=id)
