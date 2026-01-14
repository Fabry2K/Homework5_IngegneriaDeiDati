from search import Search
from figures_search import FigureSearch

def main():
    # Articoli
    s = Search()
    s.create_index()
    s.insert_documents()

    # Figure
    # fs = FigureSearch()
    # fs.create_index()
    # fs.insert_documents()

if __name__ == "__main__":
    main()