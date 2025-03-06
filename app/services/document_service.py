from sentence_transformers import SentenceTransformer
import weaviate
from weaviate.util import generate_uuid5
import uuid
from weaviate.classes.query import MetadataQuery, Filter
from app.db.weaviate_client import weaviate_client, document_class_name
from app.utils.text_processing import chunk_text

# Initialize sentence transformer model for embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

def ingest_document(document_id: str, content: str, metadata: str = None):
    """
    Ingest a document into the Weaviate database.
    
    Args:
        document_id (str): Unique identifier for the document
        content (str): Text content of the document
        metadata (str, optional): Additional metadata about the document
        
    Returns:
        dict: Information about the ingestion process
    """
    try:
        # Get the document collection
        collection = weaviate_client.collections.get(document_class_name)
        
        # Delete existing document with the same ID if it exists
        try:
            collection.data.delete_many(
                where={
                    "path": ["document_id"],
                    "operator": "Equal",
                    "valueText": document_id
                }
            )
        except Exception as e:
            # No documents to delete or other error
            print(f"Note: Failed to delete existing documents: {e}")
        
        # Chunk the document
        chunks = chunk_text(content)
        
        # Process in batch
        with collection.batch.dynamic() as batch:
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = model.encode(chunk).tolist()
                
                # Create unique ID for this chunk
                chunk_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}_{i}"))
                
                # Prepare properties
                properties = {
                    "content": chunk,
                    "document_id": document_id,
                    "chunk_id": i,
                    "metadata": metadata or ""
                }
                
                # Add to batch
                batch.add_object(
                    uuid=chunk_uuid,
                    properties=properties,
                    vector=embedding
                )
        
        return {"message": f"Document {document_id} ingested successfully", "chunks": len(chunks)}
    
    except Exception as e:
        print(f"Error ingesting document: {e}")
        raise Exception(f"Error ingesting document: {str(e)}")

def search_documents(query: str, document_id: str = None, limit: int = 3):
    """
    Search for documents that match the given query.
    
    Args:
        query (str): The search query
        document_id (str, optional): Filter results to a specific document
        limit (int): Maximum number of results to return
        
    Returns:
        dict: Search results
    """
    try:
        # Generate embedding for the query
        query_embedding = model.encode(query).tolist()
        
        # Get the collection
        collection = weaviate_client.collections.get(document_class_name)
        
        # Set up query parameters
        query_params = {
            "near_vector": query_embedding,
            "limit": limit,
            "return_metadata": MetadataQuery(distance=True)
        }
        
        # Add document_id filter if provided
        if document_id:
            query_params["filters"] = Filter.by_property("document_id").equal(document_id)
        
        # Execute the query
        response = collection.query.near_vector(**query_params)
        
        # Extract and format results
        formatted_results = []
        if response and hasattr(response, 'objects'):
            for obj in response.objects:
                result = {
                    "content": obj.properties.get("content", ""),
                    "document_id": obj.properties.get("document_id", ""),
                    "chunk_id": obj.properties.get("chunk_id", 0),
                    "metadata": obj.properties.get("metadata", "")
                }
                
                # Add distance if available
                if hasattr(obj, 'metadata') and hasattr(obj.metadata, 'distance'):
                    result["distance"] = obj.metadata.distance
                
                formatted_results.append(result)
        
        return {"results": formatted_results}
    
    except Exception as e:
        print(f"Error searching documents: {e}")
        raise Exception(f"Error searching documents: {str(e)}") 