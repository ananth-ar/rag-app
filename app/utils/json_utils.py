import json
from typing import Dict, Any, List, Optional, Union
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_json(raw_json: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalize JSON data to a standard format.
    Handles both string JSON and dictionary objects.
    
    Args:
        raw_json: The JSON data to normalize, either as a string or dict
        
    Returns:
        Dict[str, Any]: Normalized JSON data
    """
    try:
        # If input is a string, parse it
        if isinstance(raw_json, str):
            try:
                parsed_json = json.loads(raw_json)
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON string: {e}")
                raise ValueError(f"Invalid JSON string: {str(e)}")
        # If input is already a dict, return it
        elif isinstance(raw_json, dict):
            return raw_json
        # If input is a list, wrap it in a dict
        elif isinstance(raw_json, list):
            return {"items": raw_json}
        else:
            raise ValueError(f"Unsupported JSON input type: {type(raw_json)}")
    except Exception as e:
        logger.error(f"Error normalizing JSON: {e}")
        raise

def flatten_json(json_data: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested JSON structure into a flat dictionary with keys using dot notation.
    
    Args:
        json_data: The nested JSON data to flatten
        separator: The separator to use in the flattened keys
        
    Returns:
        Dict[str, Any]: Flattened JSON data
    """
    def _flatten(current_item, parent_key=''):
        items = {}
        for key, value in current_item.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.update(_flatten(value, new_key))
            elif isinstance(value, list):
                # Handle lists by adding an index to the key
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        # Recursively flatten dictionaries in lists
                        items.update(_flatten(item, f"{new_key}[{i}]"))
                    else:
                        # Add simple list items directly
                        items[f"{new_key}[{i}]"] = item
            else:
                items[new_key] = value
                
        return items
    
    # Handle the case where json_data might not be a dict
    if not isinstance(json_data, dict):
        return {"value": json_data}
    
    return _flatten(json_data)

def validate_json_query_params(field: str, operation: str) -> bool:
    """
    Validate parameters for a JSON query.
    
    Args:
        field: The field to query
        operation: The operation to perform
        
    Returns:
        bool: True if parameters are valid, False otherwise
    """
    # Check if field is provided
    if not field:
        raise ValueError("Field parameter is required")
    
    # Check if operation is supported
    valid_operations = ["max", "min", "sum", "average", "median", "count"]
    if operation not in valid_operations:
        raise ValueError(f"Invalid operation. Supported operations: {', '.join(valid_operations)}")
    
    return True 