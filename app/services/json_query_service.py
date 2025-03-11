import json
from typing import Dict, Any, List, Optional, Union
import weaviate
from weaviate.classes.query import Filter
from app.db.weaviate_client import weaviate_client, document_class_name
from app.utils.text_processing import chunk_text
from app.utils.json_utils import normalize_json, flatten_json, validate_json_query_params
import logging
import statistics

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_json_documents(document_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve JSON documents from Weaviate.
    
    Args:
        document_id (str, optional): Filter results to a specific document
        
    Returns:
        List[Dict[str, Any]]: List of JSON documents
    """
    try:
        # Get the collection
        collection = weaviate_client.collections.get(document_class_name)
        
        # Set up the query parameters
        query_params = {
            "limit": 1000  # Set a reasonable limit
        }
        
        # Add document_id filter if provided
        if document_id:
            query_params["filters"] = Filter.by_property("document_id").equal(document_id)
            logger.info(f"Filtering by document_id: {document_id}")
        
        # Execute the query
        logger.info(f"Executing query with params: {query_params}")
        response = collection.query.fetch_objects(**query_params)
        
        # Group chunks by document_id
        document_chunks = {}
        
        if response and hasattr(response, 'objects'):
            logger.info(f"Found {len(response.objects)} objects in response")
            
            # First pass: group all chunks by document_id
            for obj in response.objects:
                # Debug: Log object properties
                logger.info(f"Processing object with ID: {obj.uuid}, properties: {list(obj.properties.keys())}")
                
                # Retrieve the metadata field (may be a JSON string or a dict)
                metadata_field = obj.properties.get("metadata", "")
                logger.info(f"Metadata field type: {type(metadata_field)}, value: {metadata_field}")
                
                try:
                    # Check if metadata is a dict; if not, try to parse it
                    if isinstance(metadata_field, dict):
                        metadata = metadata_field
                        logger.info("Metadata is already a dictionary")
                    else:
                        metadata = json.loads(metadata_field) if metadata_field else {}
                        logger.info("Parsed metadata from string")
                    
                    logger.info(f"Final metadata: {metadata}")
                    
                    if metadata.get("format") == "json":
                        logger.info("Document identified as JSON format")
                        # Get document identifiers
                        doc_id = obj.properties.get("document_id", "")
                        chunk_id = obj.properties.get("chunk_id", 0)
                        content = obj.properties.get("content", "")
                        
                        # Debug: Log content preview
                        content_preview = content[:50] + "..." if len(content) > 50 else content
                        logger.info(f"Chunk {chunk_id} content preview: {content_preview}")
                        
                        # Add to document chunks dictionary
                        if doc_id not in document_chunks:
                            document_chunks[doc_id] = []
                        
                        document_chunks[doc_id].append({
                            "chunk_id": chunk_id,
                            "content": content
                        })
                        logger.info(f"Added chunk {chunk_id} to document {doc_id}")
                    else:
                        logger.info(f"Document not identified as JSON format. Format: {metadata.get('format')}")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to process metadata: {e}")
        else:
            logger.warning("Response empty or does not have 'objects' attribute")
        
        # Second pass: reconstruct complete documents and parse JSON
        json_documents = []
        
        for doc_id, chunks in document_chunks.items():
            logger.info(f"Reconstructing document {doc_id} from {len(chunks)} chunks")
            
            # Sort chunks by chunk_id to ensure correct order
            sorted_chunks = sorted(chunks, key=lambda x: x["chunk_id"])
            
            # Debug: Log first and last line of each chunk content
            for chunk in sorted_chunks:
                content_lines = chunk["content"].strip().split('\n')
                first_line = content_lines[0] if content_lines else ""
                last_line = content_lines[-1] if content_lines else ""
                logger.info(f"Chunk {chunk['chunk_id']} first line: {first_line}")
                logger.info(f"Chunk {chunk['chunk_id']} last line: {last_line}")
            
            # New approach: try to extract valid JSON objects from each chunk and collect them
            customer_objects = []
            
            for chunk in sorted_chunks:
                chunk_content = chunk["content"].strip()
                
                # Debug the chunk content
                logger.info(f"Processing chunk {chunk['chunk_id']} with content length: {len(chunk_content)}")
                
                # Try to extract customer objects from the chunk
                try:
                    # Check if this is the beginning of the array
                    if chunk_content.startswith("["):
                        chunk_content = chunk_content.lstrip("[")
                    
                    # Check if this is the end of the array
                    if chunk_content.endswith("]"):
                        chunk_content = chunk_content.rstrip("]")
                    
                    # Clean up the chunk content
                    chunk_content = chunk_content.strip()
                    
                    # If the chunk starts with a comma, remove it
                    if chunk_content.startswith(","):
                        chunk_content = chunk_content[1:].strip()
                    
                    # If the chunk ends with a comma, remove it
                    if chunk_content.endswith(","):
                        chunk_content = chunk_content[:-1].strip()
                    
                    # Extract customer objects if they are complete
                    start_idx = 0
                    while start_idx < len(chunk_content):
                        # Find the start of a potential JSON object
                        if chunk_content[start_idx] == '{':
                            # Try to find the matching closing brace
                            brace_count = 1
                            end_idx = start_idx + 1
                            while end_idx < len(chunk_content) and brace_count > 0:
                                if chunk_content[end_idx] == '{':
                                    brace_count += 1
                                elif chunk_content[end_idx] == '}':
                                    brace_count -= 1
                                end_idx += 1
                            
                            if brace_count == 0:
                                # We found a complete JSON object
                                customer_json = chunk_content[start_idx:end_idx].strip()
                                try:
                                    customer_obj = json.loads(customer_json)
                                    customer_objects.append(customer_obj)
                                    logger.info(f"Extracted customer object from chunk {chunk['chunk_id']}: {customer_obj.get('customer_id', 'unknown')}")
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse extracted customer object: {e}")
                                
                                # Move past this object
                                start_idx = end_idx
                            else:
                                # Incomplete object, move to next character
                                start_idx += 1
                        else:
                            # Not the start of an object, move to next character
                            start_idx += 1
                
                except Exception as e:
                    logger.warning(f"Error processing chunk {chunk['chunk_id']}: {e}")
            
            # If we found customer objects, add them to the document
            if customer_objects:
                json_documents.append({
                    "document_id": doc_id,
                    "content": customer_objects
                })
                logger.info(f"Successfully extracted {len(customer_objects)} customer objects for document {doc_id}")
            else:
                # Try a simpler approach: just append raw content from all chunks
                try:
                    # Try to extract customer data by adding proper JSON array wrapper
                    combined_content = "[" + ",".join([
                        chunk["content"].strip()
                            .lstrip("[").rstrip("]")  # Remove array brackets
                            .strip().rstrip(",").lstrip(",")  # Remove commas at start/end
                        for chunk in sorted_chunks
                    ]) + "]"
                    
                    # Try to parse the combined content
                    logger.info(f"Attempting to parse combined content (length: {len(combined_content)})")
                    json_data = json.loads(combined_content)
                    
                    json_documents.append({
                        "document_id": doc_id,
                        "content": json_data
                    })
                    logger.info(f"Successfully parsed combined content with {len(json_data)} objects")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing failed: {e}")
                    
                    # Last resort: try each individual chunk with proper wrapping
                    for i, chunk in enumerate(sorted_chunks):
                        try:
                            content = chunk["content"].strip()
                            # Add proper JSON array wrapping if not present
                            if not content.startswith("["):
                                content = "[" + content
                            if not content.endswith("]"):
                                content = content + "]"
                                
                            # Try to parse
                            chunk_data = json.loads(content)
                            if isinstance(chunk_data, list) and chunk_data:
                                json_documents.append({
                                    "document_id": doc_id,
                                    "chunk_id": chunk["chunk_id"],
                                    "content": chunk_data
                                })
                                logger.info(f"Successfully parsed chunk {i} with {len(chunk_data)} objects")
                        except json.JSONDecodeError:
                            continue
        
        logger.info(f"Returning {len(json_documents)} JSON documents")
        return json_documents
    
    except Exception as e:
        logger.error(f"Error retrieving JSON documents: {e}")
        raise Exception(f"Error retrieving JSON documents: {str(e)}")


def extract_values(json_data, field_path: str) -> List[Any]:
    """
    Extract values from a JSON structure based on a field path.
    Supports nested fields using dot notation (e.g., "person.address.city").
    
    Args:
        json_data: The JSON data to extract values from
        field_path: The path to the desired field
        
    Returns:
        List[Any]: List of extracted values
    """
    # First normalize the JSON to ensure it's in a consistent format
    normalized_data = normalize_json(json_data)
    
    # For complex queries, flatten the JSON to make field access easier
    if '.' in field_path:
        flattened_data = flatten_json(normalized_data)
        if field_path in flattened_data:
            return [flattened_data[field_path]]
    
    # Use recursive extraction for nested fields
    def extract_from_item(item, path_parts):
        if not path_parts:
            return [item]
        
        current = path_parts[0]
        remaining = path_parts[1:]
        
        if isinstance(item, dict):
            if current in item:
                return extract_from_item(item[current], remaining)
        elif isinstance(item, list):
            result = []
            for element in item:
                result.extend(extract_from_item(element, path_parts))
            return result
            
        return []
    
    path_parts = field_path.split('.')
    return extract_from_item(normalized_data, path_parts)


def query_json_data(document_id: Optional[str], field: str, 
                   operation: str, filter_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Perform an aggregation operation on JSON data.
    
    Args:
        document_id (str, optional): ID of the document to query
        field (str): The field to operate on
        operation (str): The operation to perform (max, min, sum, average, median, count)
        filter_criteria (Dict[str, Any], optional): Criteria to filter JSON data
        
    Returns:
        Dict[str, Any]: Result of the operation
    """
    try:
        # Validate the query parameters
        validate_json_query_params(field, operation)
        
        # Retrieve JSON documents
        json_documents = get_json_documents(document_id)
        
        if not json_documents:
            return {
                "result": None,
                "message": "No JSON documents found"
            }
        
        # Extract all field values
        all_values = []
        
        for doc in json_documents:
            content = doc["content"]
            
            # Apply filter if provided
            if filter_criteria:
                matches_filter = True
                for filter_field, filter_value in filter_criteria.items():
                    field_values = extract_values(content, filter_field)
                    if not field_values or filter_value not in field_values:
                        matches_filter = False
                        break
                
                if not matches_filter:
                    continue
            
            # Extract values for the target field
            values = extract_values(content, field)
            
            # Only include numeric values for operations that require them
            if operation in ["max", "min", "sum", "average", "median"]:
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                all_values.extend(numeric_values)
            else:
                all_values.extend(values)
        
        # Perform the requested operation
        result = None
        if all_values:
            if operation == "max":
                result = max(all_values)
            elif operation == "min":
                result = min(all_values)
            elif operation == "sum":
                result = sum(all_values)
            elif operation == "average":
                result = sum(all_values) / len(all_values)
            elif operation == "median":
                result = statistics.median(all_values)
            elif operation == "count":
                result = len(all_values)
            else:
                return {
                    "result": None,
                    "message": f"Unsupported operation: {operation}"
                }
        
        return {
            "result": result,
            "count": len(all_values),
            "operation": operation,
            "field": field,
            "document_id": document_id or "all"
        }
    
    except Exception as e:
        logger.error(f"Error performing JSON query: {e}")
        raise Exception(f"Error performing JSON query: {str(e)}") 