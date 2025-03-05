# RAG System with Weaviate

A simple Retrieval Augmented Generation (RAG) system using Weaviate as the vector database.

## Features

- Document ingestion with automatic chunking and embedding generation
- Semantic search across documents
- Support for document updates (re-ingestion)

## Setup

1. Clone the repository
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your Weaviate credentials:
   ```
   WCD_URL=your_weaviate_cloud_url
   WCD_API_KEY=your_weaviate_api_key
   ```

## Running the Application

Start the FastAPI server:

```
python main.py
```

The server will run at http://localhost:8000

## API Endpoints

### 1. Ingest Document

```
POST /documents/
```

Parameters (form data):

- `document_id`: Unique identifier for the document
- `content`: Text content of the document
- `metadata` (optional): Additional metadata about the document

Example using curl:

```
curl -X POST "http://localhost:8000/documents/" \
  -H "Content-Type: multipart/form-data" \
  -F "document_id=doc1" \
  -F "content=This is a sample document content." \
  -F "metadata={\"source\": \"example\"}"
```

### 2. Search Documents

```
GET /search/?query=your_query&document_id=optional_doc_id&limit=3
```

Parameters:

- `query`: The search query
- `document_id` (optional): Filter results to a specific document
- `limit` (optional, default=3): Maximum number of results to return

Example:

```
curl "http://localhost:8000/search/?query=sample%20content&limit=5"
```

## Next Steps

This is a barebones implementation. Future enhancements could include:

- Support for file uploads (PDF, DOCX, JSON, TXT)
- Document parsing and extraction
- More advanced chunking strategies
- Authentication and authorization
- Improved error handling and logging
