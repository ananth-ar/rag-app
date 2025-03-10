from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, BackgroundTasks
import os
import tempfile
import json
import shutil
from datetime import datetime
from app.services.document_service import ingest_document, search_documents
from app.services.service_rag import generate_rag_response
from app.services.json_query_service import query_json_data
from app.utils.document_parser import parse_document
import uuid
from pydantic import BaseModel, Field

# Create router
router = APIRouter()

# Create a temporary directory for file uploads
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "rag_uploads")
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # Test write permissions by creating and removing a test file
    test_file = os.path.join(UPLOAD_DIR, "test_permissions")
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print(f"Upload directory created successfully: {UPLOAD_DIR}")
except (PermissionError, OSError) as e:
    print(f"Error with upload directory {UPLOAD_DIR}: {str(e)}")
    # Fall back to a directory in the current project
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    print(f"Using fallback upload directory: {UPLOAD_DIR}")


@router.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {"message": "RAG System with Weaviate is running"}


@router.post("/documents")
async def process_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Smart endpoint to process any document format.
    Supports PDF, DOCX, JSON, and TXT formats.
    Automatically detects format, extracts content and metadata, and saves to the database.
    
    Args:
        file (UploadFile): The document file to upload (PDF, DOCX, JSON, or TXT)
        
    Returns:
        dict: Information about the processing results
    """
    try:
        # Generate a document ID from the filename
        base_name = os.path.splitext(file.filename)[0]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        document_id = f"{base_name}_{timestamp}"
        
        # Create a temporary file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse the document based on its format
        content, metadata_dict = parse_document(file_path)
        
        # Convert metadata to string
        metadata = json.dumps(metadata_dict)
        
        # Process the document
        result = ingest_document(document_id, content, metadata)
        
        # Clean up the temporary file
        background_tasks.add_task(os.remove, file_path)
        
        return {
            "message": f"Document processed successfully",
            "document_id": document_id,
            "format": metadata_dict.get("format", "unknown"),
            "metadata": metadata_dict,
            "chunks": result.get("chunks", 0)
        }
    except Exception as e:
        # Clean up in case of error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/")
async def search_documents_endpoint(
    query: str,
    document_id: Optional[str] = None,
    limit: int = 3
):
    """
    Endpoint to search for documents.
    
    Args:
        query (str): The search query
        document_id (str, optional): Filter results to a specific document
        limit (int): Maximum number of results to return
    
    Returns:
        dict: Search results
    """
    try:
        result = search_documents(query, document_id, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag-search/")
async def rag_search_endpoint(
    query: str,
    document_id: Optional[str] = None,
    limit: int = 3
):
    """
    Endpoint for RAG (Retrieval Augmented Generation) search using Anthropic's Claude model.
    
    Args:
        query (str): The user's question
        document_id (str, optional): Filter results to a specific document
        limit (int): Maximum number of context chunks to use
    
    Returns:
        dict: RAG response including the answer and context
    """
    try:
        result = generate_rag_response(query, document_id, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-document")
async def test_parse_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Test endpoint for parsing a document without saving to database.
    
    Args:
        file (UploadFile): The document file to parse (PDF, DOCX, JSON, or TXT)
        
    Returns:
        dict: The parsed content and metadata
    """
    file_path = None
    try:
        # Create a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save the uploaded file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to save uploaded file: {str(e)}. Path: {file_path}"
            )
        
        # Parse the document based on its format
        content, metadata_dict = parse_document(file_path)
        
        return {
            "message": "Document parsed successfully",
            "filename": file.filename,
            "format": metadata_dict.get("format", "unknown"),
            "content": content,
            "metadata": metadata_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing document: {str(e)}")
    finally:
        # Clean up the temporary file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Failed to remove temporary file {file_path}: {str(e)}")


# Model for JSON data query
class JsonQueryRequest(BaseModel):
    document_id: Optional[str] = Field(None, description="ID of the document to query (optional)")
    field: str = Field(..., description="Field to query (supports dot notation for nested fields)")
    operation: str = Field(..., description="Operation to perform (max, min, sum, average, median, count)")
    filter: Optional[Dict[str, Any]] = Field(None, description="Filter criteria (optional)")

# JSON data query endpoint
@router.post("/json-query")
async def json_query_endpoint(request: JsonQueryRequest):
    """
    Endpoint for structured queries on JSON data.
    Supports aggregation operations like max, min, sum, average, median, count.
    
    Args:
        request (JsonQueryRequest): The query request containing:
            - document_id (optional): ID of the document to query
            - field: Field to query (supports dot notation for nested fields)
            - operation: Operation to perform (max, min, sum, average, median, count)
            - filter (optional): Filter criteria to apply
    
    Returns:
        dict: Result of the operation
    """
    try:
        # Validate operation
        valid_operations = ["max", "min", "sum", "average", "median", "count"]
        if request.operation not in valid_operations:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid operation. Supported operations: {', '.join(valid_operations)}"
            )
        
        # Execute query
        result = query_json_data(
            document_id=request.document_id,
            field=request.field,
            operation=request.operation,
            filter_criteria=request.filter
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 