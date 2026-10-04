"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional
import logging
import os

# Resolve .env relative to this file's directory (backend/app/config.py → backend/.env)
# This makes loading work regardless of the current working directory.
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Neon Postgres Configuration
    database_url: str
    
    # SerpAPI Configuration
    serpapi_key: str
    
    # Gemini Configuration
    gemini_api_key: str
    
    # Embedding Configuration
    embedding_dim: int = 1536
    
    # Application Configuration
    log_level: str = "INFO"
    max_search_results: int = 10
    mock_mode: str = "false"  # "false" | "partial" | "true"
    
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def is_llm_mocked(self) -> bool:
        """Returns True if LLM calls should use mock data."""
        # Handle both old boolean format and new string format
        if isinstance(self.mock_mode, bool):
            return self.mock_mode
        return self.mock_mode.lower() in ("true", "partial")
    
    @property
    def is_db_mocked(self) -> bool:
        """Returns True if database calls should use mock data."""
        if isinstance(self.mock_mode, bool):
            return self.mock_mode
        return self.mock_mode.lower() == "true"
    
    @property
    def is_search_mocked(self) -> bool:
        """Returns True if search API calls should use mock data."""
        if isinstance(self.mock_mode, bool):
            return self.mock_mode
        return self.mock_mode.lower() == "true"
    
    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate DATABASE_URL starts with postgresql://"""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        
        v = v.strip().strip('"').strip("'")
        
        if not v.startswith('postgresql://') and not v.startswith('postgres://'):
            raise ValueError(f"DATABASE_URL must start with postgresql:// or postgres://, got: {v[:30]}...")
        
        logger.info(f"✅ Database URL validated: {v.split('@')[0]}@...")
        return v
    
    @field_validator('serpapi_key', 'gemini_api_key')
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        """Strip whitespace and quotes, check for placeholder values (skip in mock mode)."""
        # Get settings to check mock_mode - use default if not set yet
        try:
            mock_mode = info.data.get('mock_mode', True)
        except:
            mock_mode = True
        
        # In mock mode, accept placeholder values
        if mock_mode and info.field_name in ['serpapi_key', 'gemini_api_key']:
            return v or "mock_value"
        
        if not v:
            raise ValueError(f"{info.field_name} cannot be empty")
        
        # Strip whitespace and quotes
        v = v.strip().strip('"').strip("'")
        
        # Check for placeholder values
        placeholder_words = ['your-', 'placeholder', '<', '>']
        v_lower = v.lower()
        
        # Skip placeholder check for Gemini AQ. keys
        if info.field_name == 'gemini_api_key' and v.startswith('AQ.'):
            logger.info(f"✅ Gemini API key loaded: {v[:6]}...")
            return v
        
        if any(word in v_lower for word in placeholder_words):
            raise ValueError(f"{info.field_name} appears to be a placeholder: {v[:20]}...")
        
        return v


# Singleton settings instance
settings = Settings()
