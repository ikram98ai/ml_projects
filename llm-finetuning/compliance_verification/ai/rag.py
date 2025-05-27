#%pip install datasets tqdm pandas pinecone openai python-docx--quiet
import os
import pandas as pd
from docx import Document
from openai import OpenAI
from pinecone import Pinecone
from pinecone import ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

client = OpenAI( base_url="https://generativelanguage.googleapis.com/v1beta/openai/", api_key=os.getenv("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

MODEL_EMB = "text-embedding-004" 
AWS_REGION = "us-east-1"
INDEX_NAME = "pinecone-index-37cof82p4o" # "compliance-rag-index"
EMBED_DIM = 768

def get_docx(data_dir)->pd.DataFrame:
    # Initialize lists to store file information
    file_names = []
    parent_dirs = []
    word_counts = []
    file_contents = []

    # Walk through the directory and process each .docx file
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".docx"):
                file_path = os.path.join(root, file)
                parent_dir = os.path.basename(root)
                
                # Read the .docx file
                doc = Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
                word_count = len(content.split())
                
                # Append the data to the lists
                file_names.append(file.split('.doc')[0])  # Store file name without extension
                parent_dirs.append(parent_dir)
                word_counts.append(word_count)
                file_contents.append(content)

    df = pd.DataFrame({
        "pdir": parent_dirs,
        "fname": file_names,
        "word_count": word_counts,
        "content": file_contents
    })
    return df

def create_index(df:pd.DataFrame):

    # Define the Pinecone serverless specification.
    spec = ServerlessSpec(cloud="aws", region=AWS_REGION)

    # Create the index if it doesn't already exist.
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            INDEX_NAME,
            dimension=EMBED_DIM,
            metric='dotproduct',
            spec=spec
        )

    # Connect to the index.
    index = pc.Index(INDEX_NAME)

    batch_size = 32
    for i in range(0, len(df['content']), batch_size):
        i_end = min(i + batch_size, len(df['content']))
        lines_batch = df['content'][i: i_end]
        ids_batch = [str(n) for n in range(i, i_end)]
        
        # Create embeddings for the current batch.
        res = client.embeddings.create(input=[line for line in lines_batch], model=MODEL_EMB)
        embeds = [record.embedding for record in res.data]
        
        # Prepare metadata.
        meta = []
        for record in df.iloc[i:i_end].to_dict('records'):
            parent_dir = record['pdir']
            file_name = record['fname']
            content = record['content']
            # Optionally update metadata for specific entries.
            meta.append({"Licensing": parent_dir, "Name": file_name, "Content": content})
        
        # Upsert the batch into Pinecone.
        vectors = list(zip(ids_batch, embeds, meta))
        index.upsert(vectors=vectors)

    return index

def get_index():
    # Check if the index exists and return it.
    if INDEX_NAME in pc.list_indexes().names():
        return pc.Index(INDEX_NAME)
    else:
        raise ValueError(f"Index '{INDEX_NAME}' does not exist. Please create it first.")

def query_index(index, query_text)-> str:
    # Generate an embedding for the query.

    query_embedding = client.embeddings.create(input=query_text, model=MODEL_EMB).data[0].embedding

    # Query the index and return top 5 matches.
    res = index.query(vector=[query_embedding], top_k=3, include_metadata=True)

    context = "\n\n".join(
        f"Licensing: {m['metadata'].get('Licensing', '')}\nName: {m['metadata'].get('Name', '')}\nContent: {m['metadata'].get('Content', '')}"
        for m in res['matches']
    )
    return context