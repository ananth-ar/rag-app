import os
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import weaviate
from weaviate.util import generate_uuid5
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import json

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="RAG System with Weaviate")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Weaviate client
def init_weaviate_client():
    weaviate_url = os.getenv("WCD_URL")
    weaviate_api_key = os.getenv("WCD_API_KEY")
    
    if not weaviate_url or not weaviate_api_key:
        raise ValueError("Weaviate credentials not found in environment variables")
    
    auth_config = weaviate.AuthApiKey(api_key=weaviate_api_key)
    client = weaviate.Client(
        url=weaviate_url,
        auth_client_secret=auth_config
    )
    return client

# Initialize sentence transformer model for embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create Weaviate client
weaviate_client = init_weaviate_client()

# Define the class schema for documents
document_class_name = "Document"
document_class_schema = {
    "class": document_class_name,
    "vectorizer": "none",  # We'll provide our own vectors
    "properties": [
        {
            "name": "content",
            "dataType": ["text"],
            "description": "The content of the document"
        },
        {
            "name": "document_id",
            "dataType": ["string"],
            "description": "The ID of the document"
        },
        {
            "name": "chunk_id",
            "dataType": ["int"],
            "description": "The chunk ID within the document"
        },
        {
            "name": "metadata",
            "dataType": ["text"],
            "description": "Additional metadata about the document"
        }
    ]
}

# Create the schema if it doesn't exist
def create_schema_if_not_exists():
    try:
        # Check if class exists
        class_exists = weaviate_client.schema.exists(document_class_name)
        
        if not class_exists:
            weaviate_client.schema.create_class(document_class_schema)
            print(f"Created schema for class {document_class_name}")
        else:
            print(f"Schema for class {document_class_name} already exists")
    except Exception as e:
        print(f"Error creating schema: {e}")
        raise

# Create schema on startup
@app.on_event("startup")
async def startup_event():
    create_schema_if_not_exists()

# Helper function to chunk text
def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text) and end - start == chunk_size:
            # Find the last space within the chunk to avoid cutting words
            last_space = text.rfind(' ', start, end)
            if last_space != -1:
                end = last_space
        
        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else end
        
        # Break if we've reached the end
        if end == len(text):
            break
    
    return chunks

# API Endpoints
@app.get("/")
async def root():
    return {"message": "RAG System with Weaviate is running"}

@app.post("/documents/")
async def ingest_document(
    document_id: str = Form(...),
    content: str = Form(...),
    metadata: Optional[str] = Form(None)
):
    try:
        # Delete existing document with the same ID if it exists
        weaviate_client.batch.delete_objects(
            class_name=document_class_name,
            where={
                "path": ["document_id"],
                "operator": "Equal",
                "valueString": document_id
            }
        )
        
        # Chunk the document
        chunks = chunk_text(content)
        
        # Process in batch
        with weaviate_client.batch as batch:
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = model.encode(chunk).tolist()
                
                # Create unique ID for this chunk
                chunk_uuid = generate_uuid5(f"{document_id}_{i}")
                
                # Prepare properties
                properties = {
                    "content": chunk,
                    "document_id": document_id,
                    "chunk_id": i,
                    "metadata": metadata or ""
                }
                
                # Add to batch
                batch.add_data_object(
                    data_object=properties,
                    class_name=document_class_name,
                    uuid=chunk_uuid,
                    vector=embedding
                )
        
        return {"message": f"Document {document_id} ingested successfully", "chunks": len(chunks)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting document: {str(e)}")

@app.get("/search/")
async def search_documents(
    query: str,
    document_id: Optional[str] = None,
    limit: int = 3
):
    try:
        # Generate embedding for the query
        query_embedding = model.encode(query).tolist()
        
        # Prepare the search query
        search_params = {
            "vector": query_embedding,
            "limit": limit
        }
        
        # Add document_id filter if provided
        if document_id:
            search_params["where"] = {
                "path": ["document_id"],
                "operator": "Equal",
                "valueString": document_id
            }
        
        # Perform the search
        results = weaviate_client.query.get(
            document_class_name, 
            ["content", "document_id", "chunk_id", "metadata"]
        ).with_near_vector(
            search_params
        ).with_additional(["distance"]).do()
        
        # Extract and format results
        formatted_results = []
        if "data" in results and "Get" in results["data"]:
            objects = results["data"]["Get"][document_class_name]
            for obj in objects:
                formatted_results.append({
                    "content": obj["content"],
                    "document_id": obj["document_id"],
                    "chunk_id": obj["chunk_id"],
                    "metadata": obj["metadata"],
                    "distance": obj["_additional"]["distance"]
                })
        
        return {"results": formatted_results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)