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