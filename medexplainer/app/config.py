"""
Configuration settings for MedExplainer.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PubMed API
    pubmed_email: str = "medexplainer@example.com"
    pubmed_tool: str = "MedExplainer/0.1"
    
    # Redis for caching
    redis_url: str = "redis://localhost:6379/0"
    use_cache: bool = True
    
    # FastAPI
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # HuggingFace for NLP (optional)
    huggingface_token: str | None = None
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    
    class Config:
        env_file = ".env"


settings = Settings()
