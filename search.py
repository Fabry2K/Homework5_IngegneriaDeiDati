import json
from pprint import pprint
from datetime import datetime
import os
import time
import re

from dotenv import load_dotenv
from lxml import html
from elasticsearch import Elasticsearch

load_dotenv()


class Search:
    def __init__(self):
        self.es = Elasticsearch("http://localhost:9200")
        self.index_name = 'hwk5_dataing'
        print('Connected to Elasticsearch!')

    def ping(self):
        return self.es.ping()

    ###################################
    ####### Creazione dell'indice ######
    ###################################
    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name, body={
            # 'settings' : {
            #     'analysis' : {
            #         'analyzer' :{

            #             ''
            #         }
            #     }
            # },
            
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
                    abstract_parts = tree.xpath("//div[@class='ltx_abstract']//text()")
                    data = tree.xpath("//div[@class='ltx_page_logo']/text()")
                    autori = self.estrazione_autori(tree)
                    testo = tree.xpath("//section[@class='ltx_section']//text()")

                    # Pulizia
                    titolo = " ".join(t.strip() for t in titolo if t.strip())
                    abstract = " ".join(a.strip() for a in abstract_parts if a.strip())
                    abstract = self.clean_abstract(abstract)  # <-- rimuove la parola Abstract all'inizio
                    data = " ".join(d.strip() for d in data if d.strip())
                    data = self.clean_date(data)
                    testo = " ".join(t.strip() for t in testo if t.strip())

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
        return documents

    def insert_documents(self):
        index_start = time.time()
        documents = self.docs()

        for document in documents:
            self.es.index(index=self.index_name, body=document['_source'])

    ####################
    # Funzioni ausiliarie #
    ####################

    # Pulizia data --> rimozione elementi indesiderati
    def clean_date(self, data):
        data = data.replace("Generated  on ", "").replace(" by", "").strip()
        dt = datetime.strptime(data, "%a %b %d %H:%M:%S %Y")
        return dt.strftime("%Y-%m-%d")

    # Pulizia abstract --> rimuove la parola "Abstract" all'inizio
    def clean_abstract(self, abstract_text):
        if not abstract_text:
            return ""
        # Rimuove "Abstract" o "ABSTRACT" iniziale, seguito eventualmente da ':', '.' o '-'
        cleaned = re.sub(r'^\s*(Abstract|ABSTRACT)\s*[:.-]?\s*', '', abstract_text, flags=re.IGNORECASE)
        return cleaned.strip()

    # Estrazione autori
    def estrazione_autori(self, tree):
        raw_autori = tree.xpath("//span[@class='ltx_personname']//text()")
        autori = []

        for a in raw_autori:
            a = a.strip()
            if not a:
                continue
            # Rimuovi email
            if '@' in a:
                continue
            # Rimuovi comandi LaTeX tipo \authorref1
            a = re.sub(r'\\[a-zA-Z]+\d*', '', a)
            # Rimuovi numeri
            a = re.sub(r'\d+', '', a)
            # Rimuovi asterischi
            a = a.replace('*', '')
            # Normalizza spazi
            a = re.sub(r'\s+', ' ', a).strip()
            if not a:
                continue

            # Split su virgole
            parts_comma = [p.strip() for p in a.split(',') if p.strip()]

            for p in parts_comma:
                # Rimuovi & iniziali
                p = re.sub(r'^&+', '', p).strip()
                if not p:
                    continue
                # AND all'inizio → elimina
                if re.match(r'^(and)\b', p, flags=re.IGNORECASE):
                    p = re.sub(r'^(and)\b\s*', '', p, flags=re.IGNORECASE)
                    if p:
                        autori.append(p)
                    continue
                # AND in mezzo → split
                if re.search(r'\band\b', p, flags=re.IGNORECASE):
                    parts_and = re.split(r'\band\b', p, flags=re.IGNORECASE)
                    for pa in parts_and:
                        pa = pa.strip()
                        if pa:
                            autori.append(pa)
                else:
                    autori.append(p)

        # Pulizia finale: solo lettere e spazi + eliminazione di "Apple" isolato
        cleaned_autori = []
        for a in autori:
            a = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s]', '', a)
            a = re.sub(r'\s+', ' ', a).strip()
            if not a:
                continue
            if a.lower() == "apple":
                continue
            cleaned_autori.append(a)

        return cleaned_autori

    ###################
    ####### Query #######
    ###################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)

    def retrieve_document(self, id):
        return self.es.get(index=self.index_name, id=id)
