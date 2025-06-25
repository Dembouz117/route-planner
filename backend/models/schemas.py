from datetime import datetime
from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

# LangGraph State Definitions
class InformationAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    region: str
    domain_knowledge: List[Dict[str, Any]]
    disruption_data: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    analysis_complete: bool
    current_step: str

class RoutePlanningState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    upload_data: Dict[str, Any]
    information_analysis: Dict[str, Any]
    locations: List[Dict[str, Any]]
    candidate_routes: List[Dict[str, Any]]
    optimized_routes: List[Dict[str, Any]]
    final_recommendation: Dict[str, Any]
    processing_complete: bool
    current_step: str

# Pydantic Models
class LocationPoint(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    type: str  # warehouse, port, airport
    capacity: Optional[int] = None
    status: str = "active"

class DeviceForecast(BaseModel):
    model: str
    quantity: int
    destination: str
    priority: str
    delivery_window: str

class UploadData(BaseModel):
    region: str
    forecast_date: str
    device_forecasts: List[DeviceForecast]
    constraints: Dict[str, Any]

class RoutePoint(BaseModel):
    location: LocationPoint
    order: int
    estimated_arrival: Optional[str] = None

class OptimizedRoute(BaseModel):
    id: str
    points: List[RoutePoint]
    total_cost: float
    total_distance: float
    risk_score: float
    transport_mode: str
    estimated_duration: str
    status: str = "pending_approval"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizedRoute':
        """Create OptimizedRoute from dictionary data"""
        # Convert points to RoutePoint objects
        route_points = []
        for point_data in data.get("points", []):
            location_data = point_data["location"]
            location_obj = LocationPoint(**location_data)
            route_point = RoutePoint(
                location=location_obj,
                order=point_data["order"],
                estimated_arrival=point_data.get("estimated_arrival")
            )
            route_points.append(route_point)
        
        return cls(
            id=data["id"],
            points=route_points,
            total_cost=data["total_cost"],
            total_distance=data["total_distance"],
            risk_score=data["risk_score"],
            transport_mode=data["transport_mode"],
            estimated_duration=data["estimated_duration"]
        )

class AgentResult(BaseModel):
    agent_type: str
    status: str
    data: Dict[str, Any]
    timestamp: datetime