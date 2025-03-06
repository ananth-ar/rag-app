# Helper function to chunk text
def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Split text into overlapping chunks of specified size.
    
    Args:
        text (str): The text to be chunked
        chunk_size (int): Maximum size of each chunk
        overlap (int): Number of characters to overlap between chunks
        
    Returns:
        list: List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text) and end - start == chunk_size:
            # Find the last space within the chunk to avoid cutting words
            last_space = text.rfind(' ', start, end)
            if last_space != -1:
                end = last_space
        
        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else end

        if end == len(text):
            break
    
    return chunks 