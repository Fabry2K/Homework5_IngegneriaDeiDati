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
            os.getenv('ELASTIC_URL', 'http://localhost:9200'),
            verify_certs=False
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
        self.es.indices.create(
            index=self.index_name,
            body={
                'mappings': {
                    'properties': {
                        'url': {'type': 'keyword'},
                        'paper_id': {'type': 'keyword'},
                        'figure_id': {'type': 'keyword'},
                        'caption': {'type': 'text'},
                        'mentions': {'type': 'text'},
                        'semantic_context': {'type': 'text'}
                    }
                }
            }
        )

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

            paper_id = os.path.splitext(file)[0]
            full_path = os.path.join(html_path, file)

            with open(full_path, 'r', encoding='utf-8') as f:
                tree = html.fromstring(f.read())
                figures = self.extract_figures(tree, paper_id)

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
            fig = doc['_source']
            # ID deterministico: una sola entry per figura
            doc_id = f"{fig['paper_id']}_fig{fig['figure_id']}"
            self.es.index(index=self.index_name, id=doc_id, body=fig)
        print('Figures indexed successfully')

    ########################################
    #### Estrazione figure #################
    ########################################

    def extract_figures(self, tree, paper_id):
        figures_data = []

        figure_nodes = tree.xpath("//figure")
        article_base_url = f'https://arxiv.org/html/{paper_id}/'

        paragraphs = [
            p.text_content().strip()
            for p in tree.xpath("//p")
            if p.text_content().strip()
        ]

        for fig in figure_nodes:

            # URL immagine
            img_src = fig.xpath(".//img/@src")
            if not img_src:
                continue

            relative_url = img_src[0].strip()
            url = urljoin(article_base_url, relative_url)

            # Caption
            caption_tokens = fig.xpath(".//figcaption//text()")
            caption = " ".join(t.strip() for t in caption_tokens if t.strip())

            # ❌ Scarta le tabelle
            if re.match(r'^\s*table\b', caption, re.IGNORECASE):
                print("SCARTATA TABELLA:", caption[:80])
                continue

            # Estrai ID figura
            figure_id = self.extract_figure_id(caption)
            if not figure_id:
                continue

            # Paragrafi che citano la figura (fig. X)
            fig_pattern = re.compile(
                rf'\b(fig\.?|figure)\s*{figure_id}\b',
                re.IGNORECASE
            )
            mentions = [p for p in paragraphs if fig_pattern.search(p)]

            # Contesto semantico basato su soglia minima di token significativi
            caption_terms = self.extract_informative_terms(caption)
            semantic_context = []

            for p in paragraphs:
                if p in mentions:
                    continue
                if self.paragraph_matches_caption(p, caption_terms):
                    semantic_context.append(p)

            figures_data.append({
                'url': url,
                'paper_id': paper_id,
                'figure_id': figure_id,
                'caption': caption,
                'mentions': mentions,
                'semantic_context': semantic_context
            })

        return figures_data

    ########################################
    ###### Utility #########################
    ########################################

    def extract_figure_id(self, caption):
        match = re.search(
            r'\b(fig\.?|figure)\s*(\d+)',
            caption,
            re.IGNORECASE
        )
        return match.group(2) if match else None

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

    def paragraph_matches_caption(self, paragraph, caption_terms):
        """
        Restituisce True se il paragrafo contiene un numero sufficiente
        di token significativi della caption.
        """
        if not caption_terms:
            return False

        paragraph_tokens = set(re.findall(r'\b[a-zA-Z]{3,}\b', paragraph.lower()))
        match_count = len(paragraph_tokens & set(caption_terms))

        # Soglia minima: metà dei token significativi
        min_matches = max(1, len(caption_terms) // 2)

        return match_count >= min_matches

    ############################
    #### Query ################
    ############################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)
