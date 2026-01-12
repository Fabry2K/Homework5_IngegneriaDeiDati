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


from elasticsearch import Elasticsearch

class Search:
    def __init__(self):
        self.es = Elasticsearch("http://localhost:9200")
        self.index_name = 'hwk5_dataing'
        print('Connected to Elasticsearch!')



    def ping(self):
        return self.es.ping()


    ###################################
    #######Creazione dell'indice#######
    ###################################

    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name, body = { 
            
            'mappings' : {
                'properties': {
                    'titolo' : {'type' : 'text'},
                    'abstract' : {'type' : 'text'},
                    'data' : {"type": "date", "format": "yyyy-MM-dd"},
                    'autori' : {'type' : 'text'},
                    'testo' : {'type' : 'text'}
                }
            }
        })


    
    
    ###################################
    #Inserimento documenti nell'indice#
    ###################################
    
    def docs(self):
        conversion_start = time.time()
        documents = []

        textfiles_path = os.path.join('.', 'arxiv_html_papers')
        for file in os.listdir(textfiles_path):
            if file.endswith('.html'):

                #costruisco il percosrso completo del file
                full_path = os.path.join(textfiles_path, file)

                with open(full_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                    tree = html.fromstring(html_content)

                    #XPath
                    titolo = tree.xpath("//h1[@class='ltx_title ltx_title_document']/text()")    
                    abstract = tree.xpath("//div[@class='ltx_abstract']//text()")                 
                    data = tree.xpath("//div[@class='ltx_page_logo']/text()")                  
                    autori = self.estrazione_autori(tree)  
                    testo = tree.xpath("//section[@class='ltx_section']//text()")

                    #pulizia    
                    titolo = " ".join(t.strip() for t in titolo if t.strip())      #-->rimozione spazi fra righe, tab e newline
                
                    abstract = " ".join(a.strip() for a in abstract if a.strip())

                    data = " ".join(d.strip() for d in data if d.strip())               
                    data = self.clean_date(data)

                    testo = " ".join(t.strip() for t in testo if t.strip())


                    documents.append({
                        '_index' : self.index_name,
                        '_source' : {
                            'titolo' : titolo,
                            'abstract' : abstract,
                            'data' : data,
                            'autori' : autori,
                            'testo' : testo  
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
    #funzioni ausiliare#
    ####################

    #pulizia data --> rimozione elementi indesiderati
    def clean_date(self, data):
        data = data.replace("Generated  on ", "").replace(" by", "").strip()

        dt = datetime.strptime(data, "%a %b %d %H:%M:%S %Y")

        # FORMATO CORRETTO PER ELASTICSEARCH
        return dt.strftime("%Y-%m-%d")

            

        

    #estrazione autori
    def estrazione_autori(self, tree):
    
        # 1. Prendo solo i personname (uno per autore quando possibile)
        raw_autori = tree.xpath("//span[@class='ltx_personname']//text()")

        autori = []

        for a in raw_autori:
            a = a.strip()
            if not a:
                continue

            # 2. Rimuovi email
            if '@' in a:
                continue

            # 3. Rimuovi comandi LaTeX tipo \authorref1
            a = re.sub(r'\[a-zA-Z]+\d', '', a)

            # 4. Rimuovi numeri
            a = re.sub(r'\d+', '', a)

            # 5. Rimuovi asterischi
            a = a.replace('', '')

            # 6. Normalizza spazi
            a = re.sub(r'\s+', ' ', a).strip()
            if not a:
                continue

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

        # 8. Pulizia finale: solo lettere e spazi + eliminazione di "Apple" isolato
        cleaned_autori = []
        for a in autori:
            # Rimuove tutto ciò che non è lettera (unicode) o spazio
            a = re.sub(r'[^A-Za-zÀ-ÖØ-öø-ÿ\s]', '', a)
            # Normalizza spazi
            a = re.sub(r'\s+', ' ', a).strip()
            if not a:
                continue
            # Elimina "Apple" isolato
            if a.lower() == "apple":
                continue
            cleaned_autori.append(a)

        return cleaned_autori
    



    ###################
    #######Query#######
    ###################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)
    
    def retrieve_document(self, id):
        return self.es.get(index=self.index_name, id=id)