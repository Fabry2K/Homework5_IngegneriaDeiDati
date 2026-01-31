import os
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
                    'paper_id': {'type': 'keyword'},
                    'url': {'type': 'keyword'},
                    'caption': {'type': 'text'},
                    'caption_html': {'type': 'text'},
                    'citing_paragraphs': {'type': 'text'},
                    'citing_paragraphs_html': {'type': 'text'},
                    'figure_id': {'type': 'keyword'}  # aggiunto campo figura
                }
            }
        })

    ############################
    #### Indicizzazione #######
    ############################

    def docs(self):
        documents = []
        html_path = os.path.join('.', 'arxiv_html_papers')

        for file in os.listdir(html_path):
            if not file.endswith('.html'):
                continue

            paper_id = file.replace('.html', '')
            full_path = os.path.join(html_path, file)

            with open(full_path, 'r', encoding='utf-8') as f:
                tree = html.fromstring(f.read())
                figures = tree.xpath("//figure")

                article_base_url = f"https://arxiv.org/html/{paper_id}/"
                paragraphs = [p for p in tree.xpath("//p") if p.text_content().strip()]

                for idx, fig in enumerate(figures):
                    # Estrai caption
                    caption_list = fig.xpath(".//figcaption//text()")
                    caption = " ".join(c.strip() for c in caption_list if c.strip())

                    if not caption:
                        continue

                    # Escludi tabelle e algoritmi
                    if re.match(r'^(TABLE|Table|ALGORITHM|Algorithm)\b', caption):
                        continue

                    # URL immagine
                    img_src = fig.xpath(".//img/@src")
                    url = urljoin(article_base_url, img_src[0]) if img_src else None

                    # Estrai numero figura (se presente)
                    figure_number = None
                    m = re.search(r'Figure\s*(\d+)', caption, re.I)
                    if m:
                        figure_number = m.group(1)

                    # Creazione ID univoco figura: paperID_idx
                    figure_id = f"{paper_id}_{idx+1}"

                    citing_paragraphs = []
                    citing_paragraphs_html = []

                    for p in paragraphs:
                        p_text = p.text_content().strip()

                        if (
                            (figure_number and f'Figure {figure_number}' in p_text) or
                            (figure_number and f'Fig. {figure_number}' in p_text)
                        ):
                            citing_paragraphs.append(p_text)
                            citing_paragraphs_html.append(
                                html.tostring(p, encoding='unicode', method='html')
                            )

                    documents.append({
                        '_index': self.index_name,
                        '_id': figure_id,  # assegnato come _id
                        '_source': {
                            'paper_id': paper_id,
                            'url': url,
                            'caption': caption,
                            'caption_html': html.tostring(fig, encoding='unicode', method='html'),
                            'citing_paragraphs': citing_paragraphs,
                            'citing_paragraphs_html': citing_paragraphs_html,
                            'figure_id': figure_id
                        }
                    })

        return documents

    def insert_documents(self):
        documents = self.docs()

        for doc in documents:
            self.es.index(index=self.index_name, id=doc['_id'], body=doc['_source'])

        print(f"[FIGURES] Indicizzate {len(documents)} figure")

    ############################
    #### Query ################
    ############################

    def search(self, **query_args):
        return self.es.search(index=self.index_name, **query_args)
