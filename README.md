# RAG System with Weaviate

A simple Retrieval Augmented Generation (RAG) system using Weaviate as the vector database.

## Features

- Document ingestion with automatic chunking and embedding generation
- Semantic search across documents
- Support for document updates (re-ingestion)
- **File upload support for multiple formats (PDF, DOCX, JSON, TXT)**
- Automatic metadata extraction from documents
- Automatic document ID generation
- Smart document processing with format auto-detection

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

Start the FastAPI server using one of these methods:

```
# Method 1: Using the run.py script
python run.py

# Method 2: Using Uvicorn directly
uvicorn app.main:app --reload
```

The server will run at http://localhost:8000

## API Endpoints

### 1. Upload Document

```
POST /documents
```

Parameters (form data):

- `file`: The document file to upload (PDF, DOCX, JSON, or TXT)

The system will:

- Automatically detect the file format
- Extract text content and metadata
- Generate a document ID based on the filename
- Process and store the document in the vector database

Example using curl:

```
curl -X POST "http://localhost:8000/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.pdf"
```

Response:

```json
{
  "message": "Document processed successfully",
  "document_id": "document_20230512150135",
  "format": "pdf",
  "metadata": {
    "filename": "document.pdf",
    "pages": 5,
    "format": "pdf"
  },
  "chunks": 10
}
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

## Supported File Formats

The system supports the following file formats:

1. **PDF** (.pdf) - Extracts text content and metadata from PDF files
2. **DOCX** (.docx) - Extracts text content and metadata from Microsoft Word documents
3. **JSON** (.json) - Processes JSON data and extracts any embedded metadata
4. **TXT** (.txt) - Processes plain text files

## Testing Document Parsing

You can test the document parsing functionality using the provided test script:

```
python -m app.utils.test_document_parser /path/to/your/document.pdf
```

This will show you the extracted content and metadata from the document.

## Project Structure

The application is organized according to best practices for maintainability and scalability:

```
rag-app/
├── app/                    # Main application package
│   ├── __init__.py         # Package initializer
│   ├── main.py             # Application entry point and FastAPI configuration
│   ├── api/                # API endpoint definitions
│   │   ├── __init__.py
│   │   └── routes.py       # API routes for documents and search
│   ├── db/                 # Database related code
│   │   ├── __init__.py
│   │   └── weaviate_client.py  # Weaviate client and schema definitions
│   ├── services/           # Business logic and service layer
│   │   ├── __init__.py
│   │   └── document_service.py  # Document ingestion and search functionality
│   └── utils/              # Utility functions
│       ├── __init__.py
│       ├── text_processing.py   # Text chunking and processing utilities
│       └── document_parser.py   # Document parsing for different file formats
├── .env                    # Environment variables (not in version control)
├── .gitignore              # Git ignore file
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```
