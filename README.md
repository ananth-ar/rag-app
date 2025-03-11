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
- **RAG-powered answers using Anthropic's Claude model**

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
4. Create a `.env` file with your configuration:

   ```
   # Weaviate Cloud Credentials (Required)
   WCD_URL=your_weaviate_cloud_url
   WCD_API_KEY=your_weaviate_api_key

   # Anthropic API Key and Settings
   ANTHROPIC_API_KEY=your_anthropic_api_key        # Required
   ANTHROPIC_MODEL=claude-3-sonnet-20240229        # Optional, defaults to claude-3-sonnet-20240229
   ANTHROPIC_MAX_TOKENS=1000                       # Optional, defaults to 1000

   # Application Settings
   DEBUG=false                                     # Optional, defaults to false
   ```

## Docker Setup

You can also run this application using Docker:

1. Make sure you have Docker installed on your system.

2. Pull and run the application:

   ```
   docker run -p 8000:8000 --env-file .env ghcr.io/yourusername/rag-app:latest
   ```

   Or using Docker Compose:

   ```
   docker-compose up
   ```

3. Access the application at http://localhost:8000

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

### 3. RAG Search with Anthropic Claude

```
GET /rag-search/?query=your_question&document_id=optional_doc_id&limit=3
```

Parameters:

- `query`: The question you want to ask about your documents
- `document_id` (optional): Filter results to a specific document
- `limit` (optional, default=3): Maximum number of context chunks to use

Example:

```
curl "http://localhost:8000/rag-search/?query=What%20is%20the%20main%20policy%20described%20in%20the%20document%3F"
```

Response:

```json
{
  "query": "What is the main policy described in the document?",
  "answer": "Based on the provided context, the main policy described in the document appears to be a whistleblower policy. The document contains information about reporting procedures and protections for individuals who report suspected misconduct or violations.",
  "context": [
    {
      "document_id": "whistleblower-policy-ba-revised_20240308125546",
      "content": "...",
      "metadata": "...",
      "chunk_id": 1,
      "score": 0.92
    },
    {
      "document_id": "whistleblower-policy-ba-revised_20240308125546",
      "content": "...",
      "metadata": "...",
      "chunk_id": 2,
      "score": 0.85
    }
  ]
}
```

## Supported File Formats

The system supports the following file formats:

1. **PDF** (.pdf) - Extracts text content and metadata from PDF files
2. **DOCX** (.docx) - Extracts text content and metadata from Microsoft Word documents
3. **JSON** (.json) - Processes JSON data and extracts any embedded metadata
4. **TXT** (.txt) - Processes plain text files

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

## System Architecture and Design

### Architecture Overview

The RAG application follows a modular, layered architecture designed for scalability, maintainability, and extensibility:

1. **API Layer** - FastAPI endpoints that handle HTTP requests and responses
2. **Service Layer** - Core business logic for document processing, retrieval, and generation
3. **Data Layer** - Integration with Weaviate vector database for storing and querying document embeddings
4. **Utility Layer** - Helper functions for document parsing, text processing, and other utilities

### Workflow

The system operates through two main workflows:

#### Document Ingestion Workflow:

1. **Document Upload**: User uploads a document via API or UI
2. **Format Detection**: System automatically detects the file format
3. **Text Extraction**: Document is parsed using format-specific extractors
   - PDF: PyMuPDF with Tesseract OCR fallback for scanned documents
   - DOCX: python-docx for Microsoft Word documents
   - JSON: Native JSON parser with structure preservation
   - TXT: Direct text extraction
4. **Chunking**: Text is split into semantic chunks with configurable size and overlap
5. **Embedding Generation**: Sentence-Transformers model generates vector embeddings for each chunk
6. **Vector Storage**: Chunks and their embeddings are stored in Weaviate with document metadata
7. **De-duplication**: When uploading a document with the same ID, existing chunks are deleted first

#### Retrieval and Generation Workflow:

1. **Query Processing**: User submits a question via the RAG search endpoint
2. **Hybrid Search**: Weaviate performs a hybrid BM25 + vector search to find relevant text chunks
   - Vector similarity using cosine distance (all-MiniLM-L6-v2 embeddings)
   - BM25 keyword matching for lexical relevance
3. **Context Assembly**: Most relevant chunks are assembled into a context window
4. **LLM Generation**: Anthropic's Claude model generates an answer based on the retrieved context
5. **Response**: System returns the generated answer along with source context for transparency

### Design Choices and Trade-offs

#### Embedding Model Selection

- **Choice**: Using sentence-transformers' all-MiniLM-L6-v2 model
- **Advantages**: Smaller model size, faster inference, reasonable accuracy
- **Trade-offs**: Added gemini text 004 as an alternative option but couldn't fully implement due to time constraints

#### Hybrid Search Implementation

- **Choice**: Using Weaviate's hybrid search with BM25 + vector similarity
- **Advantages**: Combines lexical and semantic matching for better results
- **Trade-offs**: More complex to tune, higher latency

#### Document Chunking Strategy

- **Choice**: Fixed-size chunks with overlap and sentence boundary preservation
- **Advantages**: Preserves context, improves retrieval accuracy
- **Trade-offs**: Some storage redundancy due to overlap

#### OCR Processing

- **Choice**: Using Tesseract for scanned PDF processing
- **Advantages**: Handles documents where text extraction fails
- **Trade-offs**: Slower processing, less accurate for poor quality scans

#### Dynamic Batch Indexing

- **Choice**: Using Weaviate's batch dynamic indexing with automatic index optimization
- **Advantages**: Better ingestion performance for large documents, leverages dynamic vector indexing that starts as a flat index and automatically switches to HNSW when data exceeds ~10,000 objects
- **Trade-offs**: Slight delay before vectors are searchable

#### LLM Integration

- **Choice**: Using Anthropic's Claude model for generation
- **Advantages**: High-quality responses, good context handling
- **Trade-offs**: Initially attempted to use native Weaviate RAG capabilities but encountered integration errors; due to time limitations, implemented a custom RAG approach using Anthropic's API directly

### Challenges and Solutions

#### Challenge: Handling Scanned Documents

- **Solution**: Multi-layered extraction with OCR fallback, using PyMuPDF first and Tesseract when needed

#### Challenge: Efficient Vector Storage and Retrieval

- **Solution**: Optimized schema and batch operations with document ID-based filtering

#### Challenge: Balancing Chunk Size and Context

- **Solution**: Dynamic text chunking with overlap that preserves sentence boundaries

#### Challenge: Handling Different Document Formats

- **Solution**: Format-specific parsers with unified interface and consistent error handling

### Potential Improvements

#### Short-term Improvements

- **Implement Re-ranking**: Add a cross-encoder re-ranking step after initial retrieval to improve precision
- **Enhanced Query Preprocessing**: Implement query expansion and refinement to improve recall
- **Metadata Filtering**: Add support for filtering results based on document metadata
- **Improved OCR Pipeline**: Add image preprocessing for better OCR results on low-quality scans

#### Long-term Enhancements

- **Inverted Index Implementation**: Supplement vector search with custom inverted indices for structured data
- **Multi-modal Support**: Extend to handle images and tables within documents
- **Advanced Chunking**: Implement hierarchical chunking strategies with parent-child relationships
- **Fine-tuned Embeddings**: Train domain-specific embedding models for improved retrieval performance
- **Caching Layer**: Implement Redis caching for frequently accessed documents and queries
- **Streaming Responses**: Add support for streaming responses from the LLM for better user experience
- **Self-critique and Verification**: Implement fact-checking and answer verification mechanisms
