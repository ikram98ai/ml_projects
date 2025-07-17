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
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "apperal-compliance-v3-index")
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

def chunk_text(text:str, chunk_size=1000, chunk_overlap=200):
    """
    Splits a long text into smaller chunks of a specified size with overlap.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks

def get_data_from_dir(data_dir)->list[dict]:
    # Initialize lists to store file information
    contents: list[dict] = []
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
                
                chunks = chunk_text(content)
                for chunk in chunks:
                    contents.append({
                        "text": chunk,
                        "source": f"{parent_dir}, {fname}"
                    })
    return contents

def upsert_data(index, chunks: list[dict]) -> str:
    print(f"Upserting {len(chunks)} chunks into Pinecone index...")
    
    try:
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            i_end = min(i + batch_size, len(chunks))
            batch = chunks[i:i_end]
            
            lines_batch = [item['text'] for item in batch]
            ids_batch = [str(n) for n in range(i, i_end)]
            
            # Create embeddings for the current batch.
            res = client.embeddings.create(input=lines_batch, model=EMBED_MODEL)
            embeds = [record.embedding for record in res.data]
            
            # Prepare metadata.
            meta = []
            for item in batch:
                meta.append({"Content": item['text'], "source": item['source']})
            
            # Upsert the batch into Pinecone.
            vectors = list(zip(ids_batch, embeds, meta))
            res = index.upsert(vectors=vectors)
        print("Upsert completed successfully.")
        return f"Upsert of {len(chunks)} chunks completed successfully."
    except Exception as e:
        print(f"Error during upsert: {e}")
        return f"Error during upsert: {e}"


def search_index(index, query_text, top_k=10, filter=None):
    """Search index and return matches with metadata"""
    response = client.embeddings.create(input=query_text, model=EMBED_MODEL)
    query_embedding = response.data[0].embedding
    
    query_params = {
        "vector": [query_embedding],
        "top_k": top_k,
        "include_metadata": True
    }
    
    if filter:
        query_params["filter"] = filter
        
    res = index.query(**query_params)
    return res['matches']

def delete_vectors(index, vector_ids):
    """Delete vectors by their IDs"""
    index.delete(ids=vector_ids)

def update_vector(index, vector_id, text, source):
    """Update a vector with new text and metadata"""
    res = client.embeddings.create(input=[text], model=EMBED_MODEL)
    embedding = res.data[0].embedding
    index.upsert(vectors=[(vector_id, embedding, {"Content": text, "source": source})])

def get_vector(index, vector_id):
    """Retrieve a vector by its ID"""
    res = index.fetch(ids=[vector_id])
    if not res.vectors:
        return None
    return res.vectors.get(vector_id)


def get_paginated_vectors(index, page=1, per_page=12):

    # Get index statistics
    stats = index.describe_index_stats()
    total_vectors = stats['total_vector_count']
    
    # Calculate pagination boundaries
    offset = (page - 1) * per_page
    remaining = total_vectors - offset

    if remaining <= 0:
        return []
    
    top_k = min(per_page, remaining, 10000)
    
    # Create a dummy query vector
    dummy_vector = [0.0] * EMBED_DIM
    
    # Query with stable ordering using namespace and pagination
    res = index.query(
        vector=dummy_vector,
        top_k=top_k,
        offset=offset,
        include_metadata=True,
        include_values=False
    )
    
    return res['matches'], total_vectors

def query_index(index, query_text, top_k=7)-> tuple[float, str]:
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
        res = index.query(vector=[query_embedding], top_k=top_k, include_metadata=True)
    except Exception as e:
        print(f"Pinecone query failed: {str(e)}")
        raise ConnectionError(f"Query execution failed: {str(e)}")
        

    context ="" 
    confidence_score=0
    sources = []
    for i,m in enumerate(res['matches']):
        content = m['metadata'].get('Content', '')
        source = m['metadata'].get('source', 'Unknown source')
        score = m['score']
        context+= f"Source: {source}\nContent: {content}\n\n"
        print(f"Match {i+1}; Score: {score}; Source: {source}; Content: {content[:100]}\n")
        confidence_score+=score
        if source not in sources:
            sources.append(source)

    final_context = "LICENSING RULES FOR DETECTED ORGANIZATION:\n"
    for match in res['matches']:
        final_context += f"Source: {match['metadata'].get('source', 'N/A')}\n"
        final_context += f"{match['metadata'].get('Content', '')}\n---\n"

    return confidence_score/(i+1), final_context


def main(args):
    index = get_index()

    # Load documents from the specified directory
    if args.upsert:
        print("Upsert data into the Pinecone index.")
        contents = get_data_from_dir("ai/data")
        print(f"Found {len(contents)} documents to upsert.")
        upsert_data(index, contents)
        print("Upsert completed.")

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