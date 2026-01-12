from search import Search

def main():
    s = Search()
    #if not s.es.indices.exists(index=s.index_name):
    s.create_index()
    s.insert_documents()

if __name__ == "__main__":
    main()