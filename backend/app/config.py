"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    
    # SerpAPI Configuration
    serpapi_key: str
    
    # Gemini Configuration
    gemini_api_key: str
    
    # Embedding Configuration
    embedding_dim: int = 1536
    
    # Application Configuration
    log_level: str = "INFO"
    max_search_results: int = 10
    mock_mode: bool = True  # default True during development
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator('supabase_url', 'supabase_key', 'serpapi_key', 'gemini_api_key')
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        """Strip whitespace and quotes, check for placeholder values (skip in mock mode)."""
        # Get settings to check mock_mode - use default if not set yet
        from pydantic_settings import BaseSettings
        try:
            mock_mode = info.data.get('mock_mode', True)
        except:
            mock_mode = True
        
        # In mock mode, accept placeholder values
        if mock_mode and info.field_name in ['supabase_url', 'supabase_key', 'serpapi_key', 'gemini_api_key']:
            return v or "mock_value"
        
        if not v:
            raise ValueError(f"{info.field_name} cannot be empty")
        
        # Strip whitespace and quotes
        v = v.strip().strip('"').strip("'")
        
        # Check for placeholder values
        placeholder_words = ['your-', 'placeholder', '<', '>']
        v_lower = v.lower()
        
        # Skip placeholder check for Supabase publishable keys (sb_publishable_ is valid)
        if info.field_name == 'supabase_key' and v.startswith('sb_publishable_'):
            logger.info(f"✅ Supabase publishable key detected: {v[:20]}...")
            return v
        
        # Skip placeholder check for Gemini AQ. keys
        if info.field_name == 'gemini_api_key' and v.startswith('AQ.'):
            logger.info(f"✅ Gemini API key loaded: {v[:6]}...")
            return v
        
        if any(word in v_lower for word in placeholder_words):
            raise ValueError(f"{info.field_name} appears to be a placeholder: {v[:20]}...")
        
        return v


# Singleton settings instance
settings = Settings()
