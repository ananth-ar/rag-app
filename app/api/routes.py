from typing import Optional, List
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, BackgroundTasks
import os
import tempfile
import json
import shutil
from datetime import datetime
from app.services.document_service import ingest_document, search_documents
from app.utils.document_parser import parse_document
import uuid

# Create router
router = APIRouter()

# Create a temporary directory for file uploads
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "rag_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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


@router.post("/parse-document")
async def test_parse_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Test endpoint to parse a document and return its content and metadata.
    Supports PDF, DOCX, JSON, and TXT formats.
    Does not store the document in the database.
    
    Args:
        file (UploadFile): The document file to parse (PDF, DOCX, JSON, or TXT)
        
    Returns:
        dict: The parsed content and metadata
    """
    try:
        # Create a temporary file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Parse the document based on its format
        content, metadata_dict = parse_document(file_path)
        
        # Clean up the temporary file
        background_tasks.add_task(os.remove, file_path)
        
        return {
            "message": "Document parsed successfully",
            "filename": file.filename,
            "format": metadata_dict.get("format", "unknown"),
            "content": content,
            "metadata": metadata_dict
        }
    except Exception as e:
        # Clean up in case of error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e)) 