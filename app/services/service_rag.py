from typing import Optional, List, Dict, Any
import anthropic
from app.services.document_service import search_documents
from app.config import get_settings

def initialize_anthropic_client():
    """Initialize and return an Anthropic client using API key from environment variables."""
    settings = get_settings()
    
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return client
    except Exception as e:
        print(f"Error initializing Anthropic client: {e}")
        raise

def generate_rag_response(query: str, document_id: Optional[str] = None, limit: int = 3) -> Dict[str, Any]:
    """
    Generate a RAG response using Anthropic's Claude model.
    
    Args:
        query (str): The user's question
        document_id (str, optional): Filter results to a specific document
        limit (int): Maximum number of context chunks to use
    
    Returns:
        dict: The RAG response including the answer and context
    """
    try:
        # Initialize Anthropic client and get settings
        client = initialize_anthropic_client()
        settings = get_settings()
        
        # Search for relevant document chunks
        search_results = search_documents(query, document_id, limit)
        
        # Extract content from search results for context
        context_chunks = []
        for result in search_results["results"]:
            context_chunks.append(f"Document: {result['document_id']}\nContent: {result['content']}")
        
        context = "\n\n".join(context_chunks)
        
        # Create system prompt with RAG instructions
        system_prompt = """You are a helpful assistant that answers questions based solely on the provided context.
If the context doesn't contain the information needed to answer the question fully, acknowledge the limitations of the provided context.
Do not make up or infer information that isn't clearly supported by the context.
Always cite specific parts of the context to support your answer."""
        
        # Generate response from Claude
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.ANTHROPIC_MAX_TOKENS,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"""Context:
{context}

Question: {query}

Please answer the question based only on the provided context."""
                }
            ]
        )
        
        # Extract the assistant's response
        answer = message.content[0].text
        
        # Return RAG response with answer and context
        return {
            "query": query,
            "answer": answer,
            "context": search_results["results"]
        }
        
    except Exception as e:
        print(f"Error in RAG response generation: {e}")
        raise 