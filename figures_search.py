import os
import time
import re
from lxml import html
from urllib.parse import urljoin
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

class FigureSearch:
    def __init__(self):
        self.es = Elasticsearch(
            os.getenv('ELASTIC_URL', 'http://localhost:9200'), verify_certs=False
        )
        self.index_name = 'hwk5_figures'
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
                    'url': {'type': 'keyword'},
                    'caption': {'type': 'text'},
                    'citing_paragraphs': {'type': 'text'},
                    'semantic_context': {'type': 'text'}
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

                figures = self.extract_figures(tree, full_path)

                for fig in figures:
                    documents.append({
                        '_index': self.index_name,
                        '_source': fig
                    })

        conversion_end = time.time()
        print(f'Figures conversion time: {conversion_end - conversion_start:.3f}s')
        return documents

    def insert_documents(self):
        documents = self.docs()
        for doc in documents:
            self.es.index(index=self.index_name, body=doc['_source'])
        print('Figures indexed successfully')

    ########################################
    #### Estrazione figure (LOGICA) #######
    ########################################

    def extract_figures(self, tree, html_file):
        """
        Estrae figure con:
        - url composito corretto
        - caption
        - citing_paragraphs
        - semantic_context
        """
        figures_data = []

        # XPath per <figure>
        figure_nodes = tree.xpath("//figure")

        # Prendi nome articolo senza estensione per costruire URL
        html_filename = os.path.basename(html_file)
        article_name = os.path.splitext(html_filename)[0]
        article_base_url = f'https://arxiv.org/html/{article_name}/'

        # Tutti i paragrafi dell'articolo (per citazioni e semantic context)
        paragraphs = [p.text_content().strip() for p in tree.xpath("//p") if p.text_content().strip()]

        for fig in figure_nodes:
            # URL immagine
            relative_url_list = fig.xpath(".//img/@src")
            relative_url = relative_url_list[0].strip() if relative_url_list else None
            url = urljoin(article_base_url, relative_url) if relative_url else None

            # Caption
            caption_list = fig.xpath(".//figcaption//text()")
            caption = " ".join(c.strip() for c in caption_list if c.strip())

            # Paragrafi che citano la figura
            citing_paragraphs = [p for p in paragraphs if relative_url and relative_url in p]

            # Paragrafi che citano termini informativi della caption
            caption_terms = self.extract_informative_terms(caption)
            semantic_context = []
            for p in paragraphs:
                if p in citing_paragraphs:
                    continue  # non duplicare
                p_lower = p.lower()
                if any(term in p_lower for term in caption_terms):
                    semantic_context.append(p)

            figures_data.append({
                'url': url,
                'caption': caption,
                'citing_paragraphs': citing_paragraphs,
                'semantic_context': semantic_context
            })

        return figures_data

    ########################################
    ###### Studio del contesto #############
    ########################################

    def extract_informative_terms(self, caption):
        BASIC_STOPWORDS = {
            'the', 'of', 'and', 'in', 'to', 'for', 'with', 'on',
            'by', 'from', 'is', 'are', 'was', 'were', 'be', 'this',
            'that', 'these', 'those', 'it', 'as', 'at'
        }

        FIGURE_STOPWORDS = {
            'figure', 'fig', 'image', 'images',
            'shows', 'showing', 'results',
            'example', 'using', 'based'
        }

        STOPWORDS = BASIC_STOPWORDS | FIGURE_STOPWORDS

        tokens = re.findall(r'\b[a-zA-Z]{3,}\b', caption.lower())

        return [t for t in tokens if t not in STOPWORDS]

    ############################
    #### Query ################
    ############################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)
