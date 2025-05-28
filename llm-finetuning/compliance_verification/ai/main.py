#%pip install datasets tqdm pandas pinecone openai python-docx--quiet

from rag import get_data_from_dir, upsert_data, get_index, query_index
import argparse

def main(args):
    index = get_index()

    # Load documents from the specified directory
    if args.upsert:
        print("Upsert data into the Pinecone index.")
        contents = get_data_from_dir("ai/data")
        upsert_data(index, contents)


    print("Query the index for a specific document")
    query = input("Enter your query: ")
    result = query_index(index, query)  
    
    print(result)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="RAG Compliance Document Processing")
    parser.add_argument("--upsert", action="store_true", help="Upsert data into the index")
    args = parser.parse_args()

    main(args)