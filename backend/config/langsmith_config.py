import os
from langsmith import Client
from langchain.callbacks import LangChainTracer
from langchain.callbacks.manager import CallbackManager
from dotenv import load_dotenv

load_dotenv()

class LangSmithConfig:
    def __init__(self):
        self.enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.api_key = os.getenv("LANGSMITH_API_KEY")
        self.project = os.getenv("LANGCHAIN_PROJECT", "supply-chain-rag")
        self.endpoint = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        
        if self.enabled and self.api_key:
            self.client = Client(api_key=self.api_key, api_url=self.endpoint)
            self.tracer = LangChainTracer(project_name=self.project)
            self.callback_manager = CallbackManager([self.tracer])
        else:
            self.client = None
            self.tracer = None
            self.callback_manager = None
    
    def get_callbacks(self):
        """Get callbacks for LangChain operations"""
        return [self.tracer] if self.tracer else []
    
    def create_run(self, name: str, run_type: str = "chain", **kwargs):
        """Create a new run for tracking"""
        if self.client:
            return self.client.create_run(
                name=name,
                run_type=run_type,
                project_name=self.project,
                **kwargs
            )
        return None

langsmith_config = LangSmithConfig()