from typing import List, Dict, Any

class MockPineconeClient:
    def __init__(self):
        self.documents = [
            {"id": "doc1", "text": "Dell supply chain best practices include multi-sourcing strategies", "metadata": {"type": "guidelines"}},
            {"id": "doc2", "text": "Air freight is preferred for high-value electronics in APAC region", "metadata": {"type": "logistics"}},
            {"id": "doc3", "text": "Singapore hub serves as primary distribution center for Southeast Asia", "metadata": {"type": "facilities"}},
            {"id": "doc4", "text": "Risk mitigation strategies for geopolitical disruptions in supply chains", "metadata": {"type": "risk_management"}},
            {"id": "doc5", "text": "Cost optimization techniques for international shipping routes", "metadata": {"type": "cost_optimization"}},
        ]
    
    def query(self, query: str, top_k: int = 5) -> List[Dict]:
        """Simple mock search"""
        return [{"score": 0.9, "metadata": doc["metadata"], "text": doc["text"]} 
                for doc in self.documents if query.lower() in doc["text"].lower()][:top_k]

class MockTavilyClient:
    def __init__(self):
        self.disruptions = [
            {"title": "Red Sea shipping disruptions continue", "content": "Ongoing conflicts affecting major shipping routes", "url": "mock://news1"},
            {"title": "Port of Shanghai delays due to weather", "content": "Severe weather causing 2-day delays", "url": "mock://news2"},
            {"title": "Suez Canal traffic normalized", "content": "Normal operations resumed after temporary closure", "url": "mock://news3"},
            {"title": "Aircraft supply chain bottlenecks in Europe", "content": "Manufacturing delays affecting air freight capacity", "url": "mock://news4"},
            {"title": "Southeast Asia port congestion warning", "content": "Increased traffic causing delays at major ports", "url": "mock://news5"},
        ]
    
    def search(self, query: str) -> List[Dict]:
        """Simple mock search for disruptions"""
        return [item for item in self.disruptions if any(term in item["content"].lower() for term in query.lower().split())]