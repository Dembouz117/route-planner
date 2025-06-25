import os
from typing import Optional
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.base import BaseLanguageModel

# Load environment variables from .env file
load_dotenv()

class LLMConfig:
    """Configuration and initialization for Large Language Models"""
    
    def __init__(self):
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        print(f"Using Anthropic API Key: {self.anthropic_api_key is not None}")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        # Default to Claude Sonnet
        self.default_model = "claude-3-sonnet-20240229"
        self.default_temperature = 0.1
        self.default_max_tokens = 4000
        
        # if not self.anthropic_api_key:
        #     raise ValueError(
        #         "ANTHROPIC_API_KEY environment variable is required. "
        #         "Please set it in your .env file or environment."
        #     )
    
    def get_claude_llm(self, 
                      model: str = None, 
                      temperature: float = None, 
                      max_tokens: int = None) -> ChatAnthropic:
        """Get Claude LLM instance with specified parameters"""
        return ChatAnthropic(
            api_key=self.anthropic_api_key,
            model=model or self.default_model,
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens
        )
    
    def get_claude_haiku(self) -> ChatAnthropic:
        """Get Claude Haiku for faster, simpler tasks"""
        return ChatAnthropic(
            api_key=self.anthropic_api_key,
            model="claude-3-haiku-20240307",
            temperature=0.1,
            max_tokens=2000
        )
    
    def get_claude_opus(self) -> ChatAnthropic:
        """Get Claude Opus for most complex reasoning tasks"""
        return ChatAnthropic(
            api_key=self.anthropic_api_key,
            model="claude-3-opus-20240229",
            temperature=0.1,
            max_tokens=4000
        )
    
    def validate_api_keys(self) -> dict:
        """Validate that required API keys are available"""
        status = {
            "anthropic": bool(self.anthropic_api_key),
            "openai": bool(self.openai_api_key)
        }
        
        if not status["anthropic"]:
            raise ValueError("Anthropic API key is required for Claude models")
        
        return status

# Global LLM configuration instance
llm_config = LLMConfig()