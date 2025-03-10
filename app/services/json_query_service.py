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
        
        # Execute the query
        response = collection.query.fetch_objects(**query_params)
        
        # Filter only JSON documents
        json_documents = []
        
        if response and hasattr(response, 'objects'):
            for obj in response.objects:
                # Check if the document is a JSON document from metadata
                metadata_str = obj.properties.get("metadata", "")
                try:
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    if metadata.get("format") == "json":
                        # Parse the content as JSON
                        content = obj.properties.get("content", "")
                        try:
                            # Use the normalize_json utility to handle the JSON data
                            json_data = normalize_json(content)
                            json_documents.append({
                                "document_id": obj.properties.get("document_id", ""),
                                "chunk_id": obj.properties.get("chunk_id", 0),
                                "content": json_data
                            })
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Failed to parse JSON content: {e}")
                except json.JSONDecodeError:
                    pass
        
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