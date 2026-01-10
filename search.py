import json
from pprint import pprint
import os
import time

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()


from elasticsearch import Elasticsearch

class Search:
    def __init__(self):
        self.es = Elasticsearch("http://localhost:9200")

    def ping(self):
        return self.es.ping()

    def search(self, index, query):
        return self.es.search(
            index=index,
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["title", "abstract", "full_text"]
                }
            }
        )
    
    def create_index(self):
        self.es.indices.delete(index='hwk5_dataIng', ignore_unavailable=True)
        self.es.indices.create(index='hwk5_dataIng')


    def insert_document(self, document):
        return self.es.index(index='hwk5_dataIng', body=document)
    

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



