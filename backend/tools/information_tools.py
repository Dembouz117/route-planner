from typing import List, Dict, Any
from langchain_core.tools import tool

@tool
def search_domain_knowledge(query: str, region: str = None) -> List[Dict[str, Any]]:
    """Search Dell's internal knowledge base for supply chain information.
    
    Args:
        query: The search query for domain knowledge
        region: Optional region filter (e.g., 'APAC', 'Europe', 'Americas')
    
    Returns:
        List of relevant domain knowledge entries with content and metadata
    """
    # Mock Pinecone client simulation
    mock_documents = [
        {
            "content": "Dell supply chain best practices include multi-sourcing strategies to reduce risk",
            "relevance_score": 0.95,
            "source_type": "guidelines",
            "region": "global"
        },
        {
            "content": "Air freight is preferred for high-value electronics in APAC region due to security",
            "relevance_score": 0.88,
            "source_type": "logistics",
            "region": "APAC"
        },
        {
            "content": "Singapore hub serves as primary distribution center for Southeast Asia operations",
            "relevance_score": 0.92,
            "source_type": "facilities",
            "region": "APAC"
        },
        {
            "content": "Risk mitigation strategies for geopolitical disruptions in European supply chains",
            "relevance_score": 0.87,
            "source_type": "risk_management",
            "region": "Europe"
        },
        {
            "content": "Cost optimization techniques for international shipping routes and consolidation",
            "relevance_score": 0.85,
            "source_type": "cost_optimization",
            "region": "global"
        },
    ]
    
    # Filter based on query relevance and region
    results = []
    for doc in mock_documents:
        if query.lower() in doc["content"].lower():
            if region is None or doc["region"] == "global" or doc["region"].upper() == region.upper():
                results.append({
                    "content": doc["content"],
                    "relevance_score": doc["relevance_score"],
                    "source_type": doc["source_type"],
                    "region": doc["region"]
                })
    
    return results[:5]  # Return top 5 results


@tool
def search_supply_chain_disruptions(query: str, region: str = None) -> List[Dict[str, Any]]:
    """Search for current supply chain disruptions, port closures, wars, and geopolitical events.
    
    Args:
        query: The search query for disruptions (e.g., 'port closures', 'shipping delays')
        region: Optional region filter to focus search
    
    Returns:
        List of current disruptions affecting supply chains
    """
    # Mock Tavily/web search simulation
    mock_disruptions = [
        {
            "title": "Ben Gurion Airport Tel Aviv closed due to ongoing Middle East conflict",
            "summary": "Israel's main international airport Ben Gurion suspended operations due to security concerns, Ramon Airport in south still operational",
            "impact_level": "high",
            "region_affected": "Middle East",
            "transport_modes": ["air"],
            "source": "aviation_authority",
            "date": "2024-12-20"
        },
        {
            "title": "Red Sea shipping disruptions continue amid regional conflicts",
            "summary": "Ongoing conflicts affecting major shipping routes through Red Sea, causing 20% increase in shipping times",
            "impact_level": "high",
            "region_affected": "Middle East",
            "transport_modes": ["sea"],
            "source": "maritime_news",
            "date": "2024-12-20"
        },
        {
            "title": "Port of Shanghai experiences weather-related delays",
            "summary": "Severe weather conditions causing 2-3 day delays in container processing",
            "impact_level": "medium",
            "region_affected": "APAC",
            "transport_modes": ["sea"],
            "source": "port_authority",
            "date": "2024-12-18"
        },
        {
            "title": "Suez Canal traffic returns to normal operations",
            "summary": "Canal operations fully restored after temporary closure, backlog being cleared",
            "impact_level": "low",
            "region_affected": "Global",
            "transport_modes": ["sea"],
            "source": "suez_authority",
            "date": "2024-12-15"
        },
        {
            "title": "European air freight capacity bottlenecks reported",
            "summary": "Manufacturing delays affecting air freight capacity, 15% reduction in available cargo space",
            "impact_level": "medium",
            "region_affected": "Europe",
            "transport_modes": ["air"],
            "source": "aviation_weekly",
            "date": "2024-12-19"
        },
        {
            "title": "Southeast Asia port congestion warning issued",
            "summary": "Increased trade volumes causing delays at major APAC ports including Singapore and Hong Kong",
            "impact_level": "medium",
            "region_affected": "APAC",
            "transport_modes": ["sea"],
            "source": "trade_association",
            "date": "2024-12-17"
        },
    ]
    
    # Filter by region and query relevance
    results = []
    for disruption in mock_disruptions:
        # Check if query terms match
        query_match = any(term.lower() in disruption["title"].lower() or 
                         term.lower() in disruption["summary"].lower() 
                         for term in query.split())
        
        # Check region filter
        region_match = (region is None or 
                       region.upper() in disruption["region_affected"].upper() or
                       disruption["region_affected"] == "Global")
        
        if query_match or region_match:
            results.append({
                "title": disruption["title"],
                "summary": disruption["summary"],
                "impact_level": disruption["impact_level"],
                "region_affected": disruption["region_affected"],
                "transport_modes": disruption["transport_modes"],
                "source": disruption["source"],
                "date": disruption["date"]
            })
    
    return results[:5]


@tool
def analyze_supply_chain_risks(domain_knowledge: str, disruption_data: str) -> Dict[str, Any]:
    """Analyze and synthesize supply chain risks based on domain knowledge and current disruptions.
    
    Args:
        domain_knowledge: JSON string of domain knowledge results
        disruption_data: JSON string of disruption data results
    
    Returns:
        Comprehensive risk assessment with recommendations
    """
    import json
    
    try:
        # Parse the input data
        if isinstance(domain_knowledge, str):
            knowledge_list = json.loads(domain_knowledge)
        else:
            knowledge_list = domain_knowledge if isinstance(domain_knowledge, list) else []
            
        if isinstance(disruption_data, str):
            disruptions_list = json.loads(disruption_data)
        else:
            disruptions_list = disruption_data if isinstance(disruption_data, list) else []
    except (json.JSONDecodeError, TypeError):
        # Fallback to empty lists if parsing fails
        knowledge_list = []
        disruptions_list = []
    
    risk_factors = []
    
    # Analyze disruptions for risk levels
    for disruption in disruptions_list:
        if isinstance(disruption, dict):
            severity = disruption.get("impact_level", "medium")
            risk_factors.append({
                "type": "operational_disruption",
                "severity": severity,
                "source": disruption.get("title", "Unknown disruption"),
                "region": disruption.get("region_affected", "Global"),
                "transport_modes": disruption.get("transport_modes", ["unknown"])
            })
    
    # Analyze domain knowledge for additional risk insights
    for knowledge in knowledge_list:
        if isinstance(knowledge, dict) and "risk" in knowledge.get("content", "").lower():
            risk_factors.append({
                "type": "strategic_consideration",
                "severity": "low",
                "source": knowledge.get("content", "")[:100] + "...",
                "region": knowledge.get("region", "Global"),
                "transport_modes": ["all"]
            })
    
    # Calculate overall risk level
    high_risks = len([r for r in risk_factors if r["severity"] == "high"])
    medium_risks = len([r for r in risk_factors if r["severity"] == "medium"])
    low_risks = len([r for r in risk_factors if r["severity"] == "low"])
    
    if high_risks > 0:
        overall_risk = "high"
        risk_score = 0.8 + (high_risks * 0.1)
    elif medium_risks > 1:
        overall_risk = "medium"
        risk_score = 0.4 + (medium_risks * 0.1)
    else:
        overall_risk = "low"
        risk_score = 0.1 + (low_risks * 0.05)
    
    # Generate recommendations
    recommendations = []
    if overall_risk == "high":
        recommendations.extend([
            "Consider alternative shipping routes immediately",
            "Implement emergency sourcing procedures",
            "Increase safety stock levels by 30-50%",
            "Activate backup supplier agreements"
        ])
    elif overall_risk == "medium":
        recommendations.extend([
            "Monitor situation closely with daily updates",
            "Build 1-2 week buffer time into schedules",
            "Prepare contingency plans for route changes",
            "Consider split shipments across multiple routes"
        ])
    else:
        recommendations.extend([
            "Proceed with standard routing procedures",
            "Maintain regular monitoring schedule",
            "Continue with planned optimization initiatives"
        ])
    
    return {
        "overall_risk": overall_risk,
        "risk_score": min(risk_score, 1.0),
        "risk_factors": risk_factors,
        "total_factors_analyzed": len(risk_factors),
        "high_risk_count": high_risks,
        "medium_risk_count": medium_risks,
        "low_risk_count": low_risks,
        "key_concerns": [rf["source"] for rf in risk_factors[:3]],
        "recommendations": recommendations,
        "analysis_timestamp": "2024-12-20T10:00:00Z"
    }