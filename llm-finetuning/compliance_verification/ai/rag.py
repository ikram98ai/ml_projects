import os
from docx import Document
from openai import OpenAI
from pinecone import Pinecone
from pinecone import ServerlessSpec
from dotenv import load_dotenv
import argparse

load_dotenv()


# Initialize clients
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "apperal-compliance-openai-index")
EMBED_DIM = int(os.getenv("PINECONE_DIM", 1536))
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

client = OpenAI()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def create_index():
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
        print(f"Successfully Created Pinecone index: {PINECONE_INDEX}")


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
             
                contents.append({
                    "text": content,
                    "source": f"{parent_dir}, {fname}"
                })
    return contents

def upsert_data(contents: list[dict]) -> str:
    print(f"Upserting {len(contents)} documents into Pinecone index...")
    index = pc.Index(PINECONE_INDEX)

    try:
        batch_size = 32
        for i in range(0, len(contents), batch_size):
            i_end = min(i + batch_size, len(contents))
            batch = contents[i:i_end]
            
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
        return f"Upsert of {len(contents)} documents completed successfully."
    except Exception as e:
        print(f"Error during upsert: {e}")
        return f"Error during upsert: {e}"


def search_index(query_text, top_k=10, filter=None):
    """Search index and return matches with metadata"""
    index = pc.Index(PINECONE_INDEX)

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

def delete_vectors(vector_ids):
    """Delete vectors by their IDs"""
    index = pc.Index(PINECONE_INDEX)

    index.delete(ids=vector_ids)

def update_vector(vector_id, text, source):
    """Update a vector with new text and metadata"""
    index = pc.Index(PINECONE_INDEX)

    res = client.embeddings.create(input=[text], model=EMBED_MODEL)
    embedding = res.data[0].embedding
    index.upsert(vectors=[(vector_id, embedding, {"Content": text, "source": source})])

def get_vector(vector_id):
    """Retrieve a vector by its ID"""
    index = pc.Index(PINECONE_INDEX)

    res = index.fetch(ids=[vector_id])
    if not res.vectors:
        return None
    return res.vectors.get(vector_id)


def get_paginated_vectors(page=1, per_page=12):
    index = pc.Index(PINECONE_INDEX)
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

def query_index(query_text, top_k=5)-> tuple[float, str]:
    index = pc.Index(PINECONE_INDEX)
    print(f"Querying index with: {query_text[:100]}")
    try:
        # Generate an embedding for the query.
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
        

    final_context = "LICENSING RULES FOR DETECTED ORGANIZATION:\n"
    confidence_score=0

    for i, match in enumerate(res['matches']):
        final_context += f"Source: {match['metadata'].get('source', 'N/A')}\n"
        final_context += f"{match['metadata'].get('Content', '')}\n---\n"
        score = match['score']
        confidence_score+=score

    return confidence_score/(i+1), final_context


def main(args):
    

    # Load documents from the specified directory
    if args.upsert:
        create_index()
        print("Upsert data into the Pinecone index.")
        contents = get_data_from_dir("ai/data")
        print(f"Found {len(contents)} documents to upsert.")
        upsert_data(contents)
        print("Upsert completed.")



if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="RAG Compliance Document Processing")
    parser.add_argument("--upsert", action="store_true", help="Upsert data into the index")
    args = parser.parse_args()

    main(args)