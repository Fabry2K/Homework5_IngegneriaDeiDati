from search import Search
from figures_search import FigureSearch
from tables_search import TablesSearch # Assicurati di importare la classe giusta
from app import app 

def main():
    # Articoli
    print("Inizializzazione Articoli...")
    s = Search()
    s.create_index()
    s.insert_documents()

    # Figures
    print("Inizializzazione Figure...")
    fs = FigureSearch()
    fs.create_index()
    fs.insert_documents()

    # Tables
    print("Inizializzazione Tabelle...")
    ts = TablesSearch() # Usiamo TablesSearch, non FigureSearch
    ts.create_index()
    ts.insert_documents()

if __name__ == "__main__":
    main()