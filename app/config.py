from pydantic import BaseModel
from functools import lru_cache
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    # Weaviate settings
    WCD_URL: str = os.getenv("WCD_URL", "")
    WCD_API_KEY: str = os.getenv("WCD_API_KEY", "")
    ASYNC_INDEXING: bool = os.getenv("ASYNC_INDEXING", "True").lower() == "true"
    
    # Anthropic settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1000"))
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    def validate_settings(self) -> None:
        """Validate that all required settings are present."""
        if not self.WCD_URL:
            raise ValueError("WCD_URL is not set in environment variables")
        if not self.WCD_API_KEY:
            raise ValueError("WCD_API_KEY is not set in environment variables")
        if not self.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment variables")

@lru_cache()
def get_settings() -> Settings:
    """
    Create and validate settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    settings = Settings()
    settings.validate_settings()
    return settings 