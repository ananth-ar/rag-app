import os
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure, Property, DataType
from app.config import get_settings

# Define the document collection name
document_class_name = "Document"

def init_weaviate_client():
    """Initialize and return a Weaviate client."""
    settings = get_settings()
    
    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=settings.WCD_URL,
            auth_credentials=Auth.api_key(settings.WCD_API_KEY),
            headers={
                # Pass the required header for async indexing
                "X-Weaviate-Async-Indexing": str(settings.ASYNC_INDEXING).lower()
            }
        )
        return client
    except Exception as e:
        print(f"Error connecting to Weaviate: {e}")
        raise

# Create Weaviate client as a global variable
weaviate_client = init_weaviate_client()

def create_document_class():
    # Check if the class already exists
    if not weaviate_client.collections.exists(document_class_name):
        # Create the collection with dynamic vector index and default inverted index behavior
        collection = weaviate_client.collections.create(
            name=document_class_name,
            description="A class to store documents",
            vectorizer_config=None,  # Use 'none' vectorizer - we're adding vectors manually
            # Configure vector index as dynamic
            vector_index_config=weaviate.classes.config.Configure.VectorIndex.dynamic(),
            # Keep default inverted index behavior
            properties=[
                weaviate.classes.config.Property(
                    name="content",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Content of the document chunk"
                ),
                weaviate.classes.config.Property(
                    name="document_id",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="ID of the original document"
                ),
                weaviate.classes.config.Property(
                    name="chunk_id",
                    data_type=weaviate.classes.config.DataType.INT,
                    description="ID of the document chunk"
                ),
                weaviate.classes.config.Property(
                    name="metadata",
                    data_type=weaviate.classes.config.DataType.TEXT,
                    description="Additional metadata about the document"
                )
            ]
        )
        print(f"Class '{document_class_name}' created successfully with dynamic vector index.")
    else:
        print(f"Schema for class {document_class_name} already exists")

# Function that main.py is looking for
def create_schema_if_not_exists():
    """Create the Weaviate schema if it doesn't exist. This is called from main.py."""
    create_document_class()

# This is still called during module import, which is fine
create_document_class()