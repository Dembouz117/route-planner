import os
from typing import Optional

class LLMConfig:
    def __init__(self):
        # Load API keys from environment variables
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        # LLM configuration
        self.model_name = "claude-3-5-sonnet-20241022"
        self.temperature = 0.1
        self.max_tokens = 4000
        
        # Validate required API keys
        self._validate_config()
    
    def _validate_config(self):
        """Validate that required API keys are present"""
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        if not self.tavily_api_key:
            print("⚠️  TAVILY_API_KEY not found. Disruption search will use fallback mock data.")
    
    @property
    def is_tavily_available(self) -> bool:
        """Check if Tavily API is configured"""
        return self.tavily_api_key is not None
    
    def get_anthropic_config(self) -> dict:
        """Get configuration for Anthropic Claude"""
        return {
            "api_key": self.anthropic_api_key,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
    
    def get_tavily_config(self) -> dict:
        """Get configuration for Tavily search"""
        return {
            "api_key": self.tavily_api_key,
            "max_results": 5,
            "search_depth": "advanced"
        }

# Global configuration instance
llm_config = LLMConfig()