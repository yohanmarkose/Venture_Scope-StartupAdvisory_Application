import openai, os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from chunk_strategy import semantic_chunking
from s3 import S3FileManager
load_dotenv()

# Initialize Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Function to connect to Pinecone index
def connect_to_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    if not pc.has_index(PINECONE_INDEX):
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1",
            ),
            tags={
                "environment": "development"
            }
        )
    index = pc.Index(PINECONE_INDEX)
    return index


def read_markdown_file(file, s3_obj):
    content = s3_obj.load_s3_file_content(file)
    return content

def get_embedding(text):
    """Generates an embedding for the given text using OpenAI."""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def upsert_vectors(index, vectors):
    index.upsert(vectors=vectors, namespace=f"nvdia_quarterly_reports")

def create_pinecone_vector_store(file, chunks):
    index = connect_to_pinecone_index()
    vectors = []
    file = file.split('/')
    # parser = file[1]
    # identifier = file[2]
    year_quarter = file[2].split('-')
    year = year_quarter[1]
    quarter = year_quarter[0]
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        vectors.append((
            f"id_{year}_{quarter}_chunk_{i}",  # Unique ID
            embedding,  # Embedding vector
            {"year": year, "quarter": quarter, "text": chunk}  # Metadata
        ))
    upsert_vectors(index, vectors)
    print(f"Inserted {len(vectors)} chunks into Pinecone.")
    
    
def insert_data_into_pinecone():
    base_path = "nvca-pdfs"
    s3_obj = S3FileManager(AWS_BUCKET_NAME, base_path)

def query_pinecone(query, top_k=10, year = "2024", quarter = ["Q4"]):
    # Search the dense index and rerank the results
    index = connect_to_pinecone_index()
    dense_vector = get_embedding(query)
    results = index.query(
        namespace=f"nvdia_quarterly_reports",
        vector=dense_vector,  # Dense vector embedding
        filter={
            "year": {"$eq": year},
            "quarter": {"$in": quarter},
        },  # Sparse keyword match
        top_k=top_k,
        include_metadata=True,  # Include chunk text
    )
    responses = []
    for match in results["matches"]:
        print(f"ID: {match['id']}, Score: {match['score']}")
        # print(f"Chunk: {match['metadata']['text']}\n")
        responses.append(match['metadata']['text'])
        print("=================================================================================")
    return responses

def main():
    # Initialize Pinecone
    index = connect_to_pinecone_index()
    s3_obj = S3FileManager(AWS_BUCKET_NAME, "vc_reports")
    
    # List files in the S3 bucket
    files = s3_obj.list_files()
    files = [file for file in files if file.endswith('.md')]
    
    for file in files:
        print(f"Processing file: {file}")
        content = read_markdown_file(file, s3_obj)
        chunks = semantic_chunking(content, max_sentences=10)
        print(f"Total chunks: {len(chunks)}")
        create_pinecone_vector_store(file, chunks)
        print(f"Finished processing file: {file}")
        print("---------------------------------------------------")

if __name__ == "__main__":
    main()