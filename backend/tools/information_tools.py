from typing import List, Dict, Any

class KnowledgeSearchTool:
    def __init__(self, pinecone_client):
        self.pinecone_client = pinecone_client
    
    def search(self, query: str, region: str = None) -> List[Dict[str, Any]]:
        """Search Dell knowledge base using Pinecone"""
        results = self.pinecone_client.query(query)
        return [
            {
                "content": result["text"],
                "relevance_score": result["score"],
                "source_type": result["metadata"]["type"],
                "region": region
            }
            for result in results
        ]

class DisruptionSearchTool:
    def __init__(self, tavily_client):
        self.tavily_client = tavily_client
    
    def search(self, query: str, region: str = None) -> List[Dict[str, Any]]:
        """Search for supply chain disruptions using Tavily"""
        disruption_query = f"supply chain disruption {region or ''} port airport shipping"
        results = self.tavily_client.search(disruption_query)
        return [
            {
                "title": item["title"],
                "summary": item["content"],
                "source": item["url"],
                "impact_level": "medium",
                "region_affected": region or "global"
            }
            for item in results
        ]

class RiskAnalysisTool:
    def analyze(self, domain_knowledge: List[Dict], disruption_data: List[Dict]) -> Dict[str, Any]:
        """Analyze risks based on domain knowledge and disruption intelligence"""
        risk_factors = []
        
        # Analyze disruptions
        for disruption in disruption_data:
            if any(term in disruption["title"].lower() for term in ["war", "conflict", "blockade"]):
                risk_factors.append({"type": "geopolitical", "severity": "high", "source": disruption["title"]})
            elif any(term in disruption["title"].lower() for term in ["port", "delay", "closure"]):
                risk_factors.append({"type": "logistics", "severity": "medium", "source": disruption["title"]})
            elif any(term in disruption["title"].lower() for term in ["weather", "storm"]):
                risk_factors.append({"type": "environmental", "severity": "medium", "source": disruption["title"]})
        
        # Calculate overall risk
        high_risks = len([r for r in risk_factors if r["severity"] == "high"])
        medium_risks = len([r for r in risk_factors if r["severity"] == "medium"])
        
        if high_risks > 0:
            overall_risk = "high"
        elif medium_risks > 1:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return {
            "overall_risk": overall_risk,
            "risk_factors": risk_factors,
            "key_concerns": [rf["source"] for rf in risk_factors[:3]],
            "recommendations": [
                "Consider alternative routes" if overall_risk != "low" else "Proceed with standard routing",
                "Build buffer time" if medium_risks > 0 else "Standard timing acceptable",
                "Monitor situation closely" if high_risks > 0 else "Regular monitoring sufficient"
            ]
        }