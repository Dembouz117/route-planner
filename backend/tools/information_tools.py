import os
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

# Initialize Tavily search tool
tavily_search = TavilySearchResults(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=False,
    include_images=False,
    api_wrapper_kwargs={
        "api_key": os.environ.get("TAVILY_API_KEY")
    }
)

@tool
def search_domain_knowledge(query: str, region: str = None) -> List[Dict[str, Any]]:
    """Search Dell's internal knowledge base for supply chain information.
    
    Args:
        query: The search query for domain knowledge
        region: Optional region filter (e.g., 'APAC', 'Europe', 'Americas')
    
    Returns:
        List of relevant domain knowledge entries with content and metadata
    """
    # Mock Pinecone client simulation (replace with real Pinecone in production)
    mock_documents = [
        {
            "content": "Dell supply chain best practices include multi-sourcing strategies to reduce single points of failure and geographic concentration risks",
            "relevance_score": 0.95,
            "source_type": "guidelines",
            "region": "global",
            "document_id": "SC_BEST_001"
        },
        {
            "content": "Air freight is preferred for high-value electronics in APAC region due to security concerns and faster customs clearance",
            "relevance_score": 0.88,
            "source_type": "logistics",
            "region": "APAC",
            "document_id": "APAC_LOG_002"
        },
        {
            "content": "Singapore hub serves as primary distribution center for Southeast Asia operations with 24/7 customs clearance capability",
            "relevance_score": 0.92,
            "source_type": "facilities",
            "region": "APAC",
            "document_id": "APAC_FAC_003"
        },
        {
            "content": "Risk mitigation strategies for geopolitical disruptions in European supply chains include maintaining 30-day safety stock",
            "relevance_score": 0.87,
            "source_type": "risk_management",
            "region": "Europe",
            "document_id": "EUR_RISK_004"
        },
        {
            "content": "Cost optimization techniques for international shipping routes include consolidation hubs and intermodal transport",
            "relevance_score": 0.85,
            "source_type": "cost_optimization",
            "region": "global",
            "document_id": "SC_COST_005"
        },
        {
            "content": "Americas supply chain relies heavily on NAFTA trade corridors with key hubs in Mexico for manufacturing",
            "relevance_score": 0.83,
            "source_type": "logistics",
            "region": "Americas",
            "document_id": "AMR_LOG_006"
        },
        {
            "content": "Emergency supplier activation procedures require 48-hour notification and pre-qualified backup suppliers",
            "relevance_score": 0.90,
            "source_type": "emergency_procedures",
            "region": "global",
            "document_id": "SC_EMRG_007"
        }
    ]
    
    # Filter based on query relevance and region
    results = []
    query_terms = query.lower().split()
    
    for doc in mock_documents:
        # Check query relevance
        query_match = any(term in doc["content"].lower() for term in query_terms)
        
        # Check region filter
        region_match = (
            region is None or 
            doc["region"] == "global" or 
            doc["region"].upper() == region.upper()
        )
        
        if query_match and region_match:
            results.append({
                "content": doc["content"],
                "relevance_score": doc["relevance_score"],
                "source_type": doc["source_type"],
                "region": doc["region"],
                "document_id": doc["document_id"],
                "source": "internal_knowledge_base"
            })
    
    # Sort by relevance score and return top results
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results[:5]


@tool
def search_supply_chain_disruptions(query: str, region: str = None) -> List[Dict[str, Any]]:
    """Search for current supply chain disruptions using Tavily web search.
    
    Args:
        query: The search query for disruptions (e.g., 'port closures', 'shipping delays')
        region: Optional region filter to focus search
    
    Returns:
        List of current disruptions affecting supply chains
    """
    try:
        # Construct search query for supply chain disruptions
        search_terms = []
        
        # Add region-specific terms
        if region:
            if region.upper() == "APAC":
                search_terms.extend(["Asia Pacific", "Singapore", "Shanghai", "Hong Kong", "South China Sea"])
            elif region.upper() == "EUROPE":
                search_terms.extend(["Europe", "Mediterranean", "Suez Canal", "Rotterdam", "Hamburg"])
            elif region.upper() == "AMERICAS":
                search_terms.extend(["Americas", "North America", "Panama Canal", "Long Beach", "Los Angeles"])
            else:
                search_terms.append(region)
        
        # Add supply chain specific terms
        search_terms.extend([
            "supply chain disruption", "port closure", "shipping delay", 
            "container shortage", "freight", "logistics", "trade route"
        ])
        
        # Combine with user query
        full_query = f"{query} {' '.join(search_terms[:3])}"
        
        print(f"🔍 Searching Tavily for: {full_query}")
        
        # Use Tavily to search for real-world disruptions
        tavily_results = tavily_search.run(full_query)
        
        # Process Tavily results
        processed_results = []
        
        if isinstance(tavily_results, list):
            for result in tavily_results:
                if isinstance(result, dict):
                    # Extract relevant information
                    title = result.get("title", "Unknown disruption")
                    content = result.get("content", "")
                    url = result.get("url", "")
                    
                    # Determine impact level based on content keywords
                    impact_level = "medium"  # default
                    content_lower = content.lower() + title.lower()
                    
                    if any(word in content_lower for word in ["closed", "blocked", "suspended", "crisis", "war", "conflict"]):
                        impact_level = "high"
                    elif any(word in content_lower for word in ["delayed", "congestion", "slow", "shortage"]):
                        impact_level = "medium"
                    elif any(word in content_lower for word in ["minor", "resolved", "improving", "normal"]):
                        impact_level = "low"
                    
                    # Determine affected transport modes
                    transport_modes = []
                    if any(word in content_lower for word in ["port", "ship", "vessel", "container", "maritime"]):
                        transport_modes.append("sea")
                    if any(word in content_lower for word in ["airport", "flight", "cargo plane", "air freight"]):
                        transport_modes.append("air")
                    if any(word in content_lower for word in ["truck", "rail", "train", "highway", "border"]):
                        transport_modes.append("land")
                    
                    if not transport_modes:
                        transport_modes = ["sea", "air", "land"]  # assume affects all if unclear
                    
                    # Determine affected region
                    region_affected = "Global"
                    if any(word in content_lower for word in ["asia", "pacific", "china", "singapore", "japan"]):
                        region_affected = "APAC"
                    elif any(word in content_lower for word in ["europe", "mediterranean", "suez", "rotterdam"]):
                        region_affected = "Europe" 
                    elif any(word in content_lower for word in ["america", "us", "canada", "mexico", "panama"]):
                        region_affected = "Americas"
                    elif any(word in content_lower for word in ["middle east", "red sea", "persian gulf"]):
                        region_affected = "Middle East"
                    
                    processed_results.append({
                        "title": title,
                        "summary": content[:200] + "..." if len(content) > 200 else content,
                        "impact_level": impact_level,
                        "region_affected": region_affected,
                        "transport_modes": transport_modes,
                        "source": "tavily_web_search",
                        "url": url,
                        "date": "2024-12-20"  # Could extract from content if available
                    })
        
        print(f"✅ Found {len(processed_results)} disruptions via Tavily")
        return processed_results[:5]  # Return top 5 results
        
    except Exception as e:
        print(f"❌ Tavily search failed: {e}")
        
        # Fallback to mock data if Tavily fails
        mock_disruptions = [
            {
                "title": "Red Sea shipping disruptions continue amid regional conflicts",
                "summary": "Ongoing conflicts affecting major shipping routes through Red Sea, causing 20% increase in shipping times",
                "impact_level": "high",
                "region_affected": "Global",
                "transport_modes": ["sea"],
                "source": "fallback_mock_data",
                "url": "mock://fallback",
                "date": "2024-12-20"
            },
            {
                "title": "Port congestion reported at major Asian hubs",
                "summary": "Increased trade volumes causing delays at Singapore and Shanghai ports",
                "impact_level": "medium",
                "region_affected": "APAC",
                "transport_modes": ["sea"],
                "source": "fallback_mock_data", 
                "url": "mock://fallback",
                "date": "2024-12-20"
            }
        ]
        
        # Filter mock data by region if specified
        if region:
            mock_disruptions = [d for d in mock_disruptions 
                             if d["region_affected"] == "Global" or region.upper() in d["region_affected"].upper()]
        
        return mock_disruptions


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
    from datetime import datetime
    
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
                "transport_modes": disruption.get("transport_modes", ["unknown"]),
                "url": disruption.get("url", "")
            })
    
    # Analyze domain knowledge for additional risk insights
    for knowledge in knowledge_list:
        if isinstance(knowledge, dict) and "risk" in knowledge.get("content", "").lower():
            risk_factors.append({
                "type": "strategic_consideration",
                "severity": "low",
                "source": knowledge.get("content", "")[:100] + "...",
                "region": knowledge.get("region", "Global"),
                "transport_modes": ["all"],
                "document_id": knowledge.get("document_id", "")
            })
    
    # Calculate overall risk level
    high_risks = len([r for r in risk_factors if r["severity"] == "high"])
    medium_risks = len([r for r in risk_factors if r["severity"] == "medium"])
    low_risks = len([r for r in risk_factors if r["severity"] == "low"])
    
    if high_risks > 0:
        overall_risk = "high"
        risk_score = min(0.8 + (high_risks * 0.1), 1.0)
    elif medium_risks > 1:
        overall_risk = "medium"
        risk_score = 0.4 + (medium_risks * 0.1)
    else:
        overall_risk = "low"
        risk_score = 0.1 + (low_risks * 0.05)
    
    # Generate recommendations based on risk level and factors
    recommendations = []
    if overall_risk == "high":
        recommendations.extend([
            "IMMEDIATE: Consider alternative shipping routes",
            "URGENT: Implement emergency sourcing procedures",
            "Increase safety stock levels by 30-50%",
            "Activate backup supplier agreements",
            "Daily monitoring of disruption status required"
        ])
    elif overall_risk == "medium":
        recommendations.extend([
            "Monitor situation closely with daily updates",
            "Build 1-2 week buffer time into delivery schedules",
            "Prepare contingency plans for route changes",
            "Consider split shipments across multiple routes",
            "Review supplier diversification options"
        ])
    else:
        recommendations.extend([
            "Proceed with standard routing procedures",
            "Maintain regular monitoring schedule",
            "Continue with planned optimization initiatives",
            "Monitor for emerging risks weekly"
        ])
    
    # Add transport mode specific recommendations
    affected_modes = set()
    for factor in risk_factors:
        affected_modes.update(factor.get("transport_modes", []))
    
    if "sea" in affected_modes and high_risks > 0:
        recommendations.append("Consider air freight alternatives for urgent shipments")
    if "air" in affected_modes and high_risks > 0:
        recommendations.append("Evaluate sea freight options despite longer transit times")
    
    return {
        "overall_risk": overall_risk,
        "risk_score": round(risk_score, 3),
        "risk_factors": risk_factors,
        "total_factors_analyzed": len(risk_factors),
        "high_risk_count": high_risks,
        "medium_risk_count": medium_risks,
        "low_risk_count": low_risks,
        "key_concerns": [rf["source"] for rf in risk_factors[:3]],
        "affected_transport_modes": list(affected_modes),
        "recommendations": recommendations,
        "analysis_timestamp": datetime.now().isoformat(),
        "data_sources": {
            "domain_knowledge_items": len(knowledge_list),
            "disruption_sources": ["tavily_web_search" if any("tavily" in str(d) for d in disruptions_list) else "mock_data"],
            "knowledge_base": "internal_pinecone_simulation"
        }
    }