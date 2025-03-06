import os
import sys
import json

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.utils.document_parser import parse_document

def test_document_parser(file_path):
    """
    Test the document parser with a given file.
    
    Args:
        file_path (str): Path to the document to test
    """
    try:
        print(f"Testing document parser with file: {file_path}")
        
        # Get the file extension
        file_extension = os.path.splitext(file_path)[1].lower()
        print(f"File extension: {file_extension}")
        
        # Parse the document
        content, metadata = parse_document(file_path)
        
        # Print the results
        print("\nMetadata:")
        print(json.dumps(metadata, indent=2))
        
        print("\nContent preview (first 500 chars):")
        print(content[:500] + "..." if len(content) > 500 else content)
        
        print("\nContent length:", len(content))
        
        return True
    except Exception as e:
        print(f"Error testing document parser: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if a file path was provided
    if len(sys.argv) < 2:
        print("Usage: python test_document_parser.py <file_path>")
        sys.exit(1)
    
    # Get the file path from the command line arguments
    file_path = sys.argv[1]
    
    # Test the document parser
    success = test_document_parser(file_path)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 