import os
from docx import Document
from openai import OpenAI
from pinecone import Pinecone
from pinecone import ServerlessSpec
from dotenv import load_dotenv
import argparse
import traceback

load_dotenv()


# Initialize clients
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "apperal-compliance-v2-index")
EMBED_DIM = int(os.getenv("PINECONE_DIM", 1536))
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

client = OpenAI()

def get_index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    # Create the index if it doesn't already exist.
    if PINECONE_INDEX not in pc.list_indexes().names():
        print(f"Creating Pinecone index: {PINECONE_INDEX}")
        # Define the Pinecone serverless specification.
        spec = ServerlessSpec(cloud="aws", region=PINECONE_REGION)
        pc.create_index(
            PINECONE_INDEX,
            dimension=EMBED_DIM,
            metric='dotproduct',
            spec=spec
        )

    # Connect to the index.
    index = pc.Index(PINECONE_INDEX)
    # print('Connected to Pinecone index:', PINECONE_INDEX,'\n', index)
    return index


def get_data_from_dir(data_dir)->list[str]:
    # Initialize lists to store file information
    contents: list[str] = []
    # Walk through the directory and process each .docx file
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".docx"):
                file_path = os.path.join(root, file)
                parent_dir = os.path.basename(root)
                # Read the .docx file
                doc = Document(file_path)
                fname = file.split('.doc')[0]
                content = "\n".join([para.text for para in doc.paragraphs])

                contents.append( parent_dir + ", " + fname + ", " + content)  
    return contents

def upsert_data(index, contents: list[str]) -> None:
    print(f"Upserting data with length {len(contents)} into Pinecone index...")
    
    try:
        batch_size = 32
        for i in range(0, len(contents), batch_size):
            i_end = min(i + batch_size, len(contents))
            lines_batch = contents[i: i_end]
            ids_batch = [str(n) for n in range(i, i_end)]
            
            # Create embeddings for the current batch.
            res = client.embeddings.create(input=[line[:1536] for line in lines_batch], model=EMBED_MODEL)
            embeds = [record.embedding for record in res.data]
            
            # Prepare metadata.
            meta = []
            for content in contents[i:i_end]:
                meta.append({"Content": content})
            # Upsert the batch into Pinecone.
            vectors = list(zip(ids_batch, embeds, meta))
            res = index.upsert(vectors=vectors)
        print("Upsert completed successfully.")
        return f"Upsert {len(contents)} files, completed successfully."
    except Exception as e:
        print(f"Error during upsert: {e}")
        return f"Error during upsert: {e}"


def query_index(index, query_text)-> tuple[float, str]:
    # Generate an embedding for the query.
    print(f"Querying index with: {query_text[:100]}")
    # index = get_index()
    try:
        response = client.embeddings.create(input=query_text, model=EMBED_MODEL)
        if not response or not response.data or not response.data[0].embedding:
            raise ValueError("Embedding generation returned no data.")
        query_embedding = response.data[0].embedding
    except Exception as e:
        print(f"Failed to create query embedding: {str(e)}")
        raise ConnectionError(f"Embedding generation failed: {str(e)}")
    
    # Query the index and return top_k matches.
    try:
        res = index.query(vector=[query_embedding], top_k=1, include_metadata=True)
    except Exception as e:
        print(f"Pinecone query failed: {str(e)}")
        raise ConnectionError(f"Query execution failed: {str(e)}")
        

    context ="" 
    confidence_score=0
    for i,m in enumerate(res['matches']):
        content = m['metadata'].get('Content', '')
        score = m['score']
        context+= f"{content}\n"
        print(f"License: {i+1}; Score: {score}; Content: {content[:100]}\n")
        confidence_score+=score
    # return f"Confidence score: {int(rag_score/(i+1)*100)}\n{context}"
    return confidence_score/(i+1), "LICENSING RULES FOR DETECTED ORGANIZATION: " + context



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