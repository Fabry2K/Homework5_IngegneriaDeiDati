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

