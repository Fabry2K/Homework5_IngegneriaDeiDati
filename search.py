from pprint import pprint
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
                    tree = html.fromstring(f.read())

                    # XPath
                    titolo = tree.xpath("//h1[@class='ltx_title ltx_title_document']/text()")    
                    abstract = tree.xpath("//div[@class='ltx_abstract']//text()")                 
                    data = tree.xpath("//div[@class='ltx_page_logo']/text()")                  
                    autori = estrazione_autori(tree)  

                    # concatena tutte le sezioni in un unico testo HTML interpretabile
                    sections = tree.xpath("//section[@class='ltx_section']")
                    testo_blocks = []
                    for sec in sections:
                        # Rimuovi solo note, mantieni resto HTML
                        for note in sec.xpath('.//span[contains(@class,"ltx_note")]'):
                            note.getparent().remove(note)
                        testo_blocks.append(html.tostring(sec, encoding='unicode', method='html').strip())
                    testo = "\n".join(testo_blocks)

                    # Pulizia
                    titolo = " ".join(t.strip() for t in titolo if t.strip())
                    abstract = " ".join(a.strip() for a in abstract if a.strip())
                    abstract = clean_abstract(abstract)
                    data = " ".join(d.strip() for d in data if d.strip())               
                    data = clean_date(data)

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


    ###################
    ###### Query ######
    ###################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)

    def retrieve_document(self, id):
        return self.es.get(index=self.index_name, id=id)
    


    ####TODO####

    ## figure class="ltx_table"