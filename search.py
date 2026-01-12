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

    # def search(self, index, query):
    #     return self.es.search(
    #         index=index,
    #         query={
    #             "multi_match": {
    #                 "query": query,
    #                 "fields": ["title", "abstract", "full_text"]
    #             }
    #         }
    #     )
    




    ###################################
    #######Creazione dell'indice#######
    ###################################

    def create_index(self):
        self.es.indices.delete(index=self.index_name, ignore_unavailable=True)
        self.es.indices.create(index=self.index_name)

    
    
    ###################################
    #Inserimento documenti nell'indice#
    ###################################

    def insert_document(self, document):
        return self.es.index(index=self.index_name, body=document)
    
    
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
                    testo = tree.xpath("//section[@class='ltx_section']/text()")

                    #pulizia    
                    titolo = " ".join(t.strip() for t in titolo if t.strip())      #-->rimozione spazi fra righe, tab e newline
                
                    abstract = " ".join(a.strip() for a in abstract if a.strip())

                    data = " ".join(d.strip() for d in data if d.strip())               
                    data = self.clean_date(data)



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
            print(document['_source']['autori'], end="\n\n")

    


    ####################
    #funzioni ausiliare#
    ####################

    #pulizia data --> rimozione elementi indesiderati
    def clean_date(self, data):

        data = re.sub(r"\bGenerated on\b", "", data, flags=re.IGNORECASE)
        data = re.sub(r"\bby\b", "", data, flags=re.IGNORECASE)

        data = re.sub(r"\b\d{2}:\d{2}:\d{2}\b", "", data)


        return " ".join(data.split())


    #conversione data in formato yyyy/mm/dd
    def to_iso_date(self, data):

        data = datetime.strptime(data, "%a %b %d %Y")
        return data.strftime("%Y-%m-%d")
        

        

    #estrazione autori
    def estrazione_autori(self, tree):
        autori = tree.xpath("//span[@class='ltx_personname']/text() | //p[@id='p1.3']/text()")
        autori = " ".join(a.strip() for a in autori if a.strip())
        
        # Rimuovi le virgole finali
        autori = re.sub(r',$', '', autori, flags=re.MULTILINE)

        # Rimuovi i tag del tipo \qualcosa (compresi eventuali numeri)
        autori = re.sub(r'\\[a-zA-Z]+\d*', '', autori)

        # Rimuovi eventuali spazi extra
        autori = re.sub(r'\s+', ' ', autori)

        # Dividi per riga e ripulisci eventuali spazi all'inizio/fine
        array_autori = [line.strip() for line in autori.split('\n') if line.strip()]

        return array_autori






    #authors: "ltx_title ltx_titledocument" --- "ltx_personname", "ltx_document ltx_authors_1line"--> in questo caso restituire il contenuto intero del nipote <p>, ltx_abstract,  



    # *****TODO*****
    # Xpath per data:
    # //div[@class='ltx_page_logo']
    # estrarre data

    # Xpath per abstract:
    # //div[@class='ltx_abstract']

    # Xpath per titolo:
    # //h1[@class='ltx_title ltx_title_document']
    # !! togliere \n


    # Xpath per autori:
    # //span[@class='ltx_personname'] | //article[@class='ltx_document ltx_authors_1line']/div[1][@id='p1']/p[@id='p1.3']
    # !! sanificare dai tag con '/' ; togliere numeri  ;  punteggiatura

    # Xpath per testo:
    # //section[@class='ltx_section']
    # !! togliere comandi per caratteri speciali fatti con '{\comando}'



