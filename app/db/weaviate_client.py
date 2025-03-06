import os
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType

# Define the document collection name
document_class_name = "Document"

def init_weaviate_client():
    """Initialize and return a Weaviate client."""
    weaviate_url = os.getenv("WCD_URL")
    weaviate_api_key = os.getenv("WCD_API_KEY")
    
    if not weaviate_url or not weaviate_api_key:
        raise ValueError("Weaviate credentials not found in environment variables")
    
    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=Auth.api_key(weaviate_api_key)
        )
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate: {e}")
        raise

# Create Weaviate client as a global variable
weaviate_client = init_weaviate_client()

def create_schema_if_not_exists():
    """Create the schema for document collection if it doesn't exist."""
    try:
        # Check if collection exists by trying to get it
        try:
            weaviate_client.collections.get(document_class_name)
            print(f"Schema for class {document_class_name} already exists")
            return
        except Exception:
            # Collection doesn't exist, create it
            pass
        
        # Create collection with properties
        weaviate_client.collections.create(
            name=document_class_name,
            vectorizer_config=Configure.Vectorizer.none(),  # We'll provide our own vectors
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="document_id", data_type=DataType.TEXT),
                Property(name="chunk_id", data_type=DataType.INT),
                Property(name="metadata", data_type=DataType.TEXT)
            ]
        )
        print(f"Created schema for class {document_class_name}")
    except Exception as e:
        print(f"Error creating schema: {e}")
        raise 