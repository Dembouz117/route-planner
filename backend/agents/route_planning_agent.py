import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage
from models.schemas import RoutePlanningState, OptimizedRoute, RoutePoint, LocationPoint
from tools.route_planning_tools import DistanceCalculatorTool, CostEstimatorTool, RouteOptimizerTool
from datetime import datetime

class RoutePlanningAgent:
    def __init__(self):
        # Initialize tools
        self.distance_tool = DistanceCalculatorTool()
        self.cost_tool = CostEstimatorTool()
        self.optimizer_tool = RouteOptimizerTool()
        
        # Create workflow
        self.workflow = self._create_workflow()
    
    def _create_workflow(self):
        """Create the Route Planning Agent LangGraph workflow"""
        workflow = StateGraph(RoutePlanningState)
        
        # Add nodes
        workflow.add_node("route_generation", self._route_generation_node)
        workflow.add_node("cost_analysis", self._cost_analysis_node)
        workflow.add_node("risk_assessment", self._risk_assessment_node)
        workflow.add_node("optimization", self._optimization_node)
        
        # Add edges
        workflow.add_edge(START, "route_generation")
        workflow.add_edge("route_generation", "cost_analysis")
        workflow.add_edge("cost_analysis", "risk_assessment")
        workflow.add_edge("risk_assessment", "optimization")
        workflow.add_edge("optimization", END)
        
        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _route_generation_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node: Generate candidate routes based on upload data"""
        print("🚚 Route Planning Agent: Generating candidate routes")
        
        upload_data = state["upload_data"]
        all_locations = state["locations"]
        
        candidate_routes = []
        
        # Generate routes for each device forecast
        for forecast in upload_data.get("device_forecasts", []):
            destination = forecast["destination"].lower()
            
            # Find suitable origin and destination points
            origin_candidates = [loc for loc in all_locations if "singapore" in loc["name"].lower() or "hub" in loc["name"].lower()]
            dest_candidates = [loc for loc in all_locations if destination in loc["name"].lower()]
            
            if not origin_candidates or not dest_candidates:
                origin_candidates = all_locations[:1]
                dest_candidates = all_locations[1:2]
            
            origin = origin_candidates[0]
            destination_loc = dest_candidates[0]
            
            # Calculate distance
            distance = self.distance_tool.calculate(
                origin["lat"], origin["lng"], 
                destination_loc["lat"], destination_loc["lng"]
            )
            
            # Generate route variants with different transport modes
            transport_modes = ["air", "sea", "land"] if distance > 500 else ["land", "air"]
            
            for transport_mode in transport_modes:
                # Create route waypoints
                waypoints = [
                    {"location": origin, "order": 1, "estimated_arrival": None},
                    {"location": destination_loc, "order": 2, "estimated_arrival": None}
                ]
                
                # Add intermediate waypoint for long routes
                if distance > 2000 and len(all_locations) > 2:
                    intermediate_locations = [loc for loc in all_locations if loc != origin and loc != destination_loc]
                    if intermediate_locations:
                        waypoints.insert(1, {"location": intermediate_locations[0], "order": 2, "estimated_arrival": None})
                        waypoints[2]["order"] = 3
                
                route = {
                    "id": str(uuid.uuid4()),
                    "forecast_id": forecast.get("model", "unknown"),
                    "points": waypoints,
                    "total_distance": round(distance, 2),
                    "transport_mode": transport_mode,
                    "quantity": forecast["quantity"],
                    "priority": forecast["priority"]
                }
                
                candidate_routes.append(route)
        
        state["candidate_routes"] = candidate_routes
        state["current_step"] = "routes_generated"
        state["messages"].append(
            AIMessage(content=f"Generated {len(candidate_routes)} candidate routes")
        )
        
        return state
    
    def _cost_analysis_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node: Analyze costs for each candidate route"""
        print("💰 Route Planning Agent: Analyzing route costs")
        
        info_analysis = state["information_analysis"]
        risk_multiplier = 1.0
        
        # Determine risk multiplier from information analysis
        if info_analysis and "risk_assessment" in info_analysis:
            risk_level = info_analysis["risk_assessment"].get("overall_risk", "low")
            risk_multiplier = {"low": 1.0, "medium": 1.3, "high": 1.6}.get(risk_level, 1.0)
        
        # Calculate costs for each route
        for route in state["candidate_routes"]:
            cost = self.cost_tool.estimate(
                route["total_distance"],
                route["transport_mode"],
                route["quantity"],
                risk_multiplier
            )
            route["total_cost"] = round(cost, 2)
        
        state["current_step"] = "costs_analyzed"
        state["messages"].append(
            AIMessage(content=f"Cost analysis complete with risk multiplier: {risk_multiplier}")
        )
        
        return state
    
    def _risk_assessment_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node: Assess risks for each route based on disruption intelligence"""
        print("⚠️ Route Planning Agent: Assessing route risks")
        
        info_analysis = state["information_analysis"]
        base_risk = 0.2
        
        # Calculate risk scores based on disruption data
        for route in state["candidate_routes"]:
            risk_score = base_risk
            
            # Increase risk based on disruption intelligence
            if info_analysis and "disruption_data" in info_analysis:
                for disruption in info_analysis["disruption_data"]:
                    # Check if disruption affects this route's transport mode or region
                    if route["transport_mode"] == "sea" and "port" in disruption.get("title", "").lower():
                        risk_score += 0.3
                    elif route["transport_mode"] == "air" and "airport" in disruption.get("title", "").lower():
                        risk_score += 0.3
                    elif "shipping" in disruption.get("title", "").lower():
                        risk_score += 0.2
            
            # Increase risk for longer routes
            if route["total_distance"] > 5000:
                risk_score += 0.1
            
            route["risk_score"] = min(round(risk_score, 2), 1.0)
        
        state["current_step"] = "risks_assessed"
        state["messages"].append(
            AIMessage(content="Risk assessment complete for all candidate routes")
        )
        
        return state
    
    def _optimization_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node: Optimize and rank routes"""
        print("🎯 Route Planning Agent: Optimizing route selection")
        
        # Optimize routes
        optimized_routes = self.optimizer_tool.optimize(state["candidate_routes"])
        
        # Add duration estimates
        for route in optimized_routes:
            transport_factors = {"air": 0.1, "sea": 1.0, "land": 0.5}
            factor = transport_factors.get(route["transport_mode"], 0.5)
            duration_days = max(1, int(route["total_distance"] * factor / 500))
            route["estimated_duration"] = f"{duration_days} days"
        
        # Create final recommendation
        top_routes = [r for r in optimized_routes if r.get("recommended", False)]
        
        final_recommendation = {
            "recommended_routes": top_routes[:3],
            "total_routes_analyzed": len(optimized_routes),
            "average_cost": round(sum(r["total_cost"] for r in optimized_routes) / len(optimized_routes), 2),
            "average_risk": round(sum(r["risk_score"] for r in optimized_routes) / len(optimized_routes), 2),
            "optimization_timestamp": datetime.now().isoformat()
        }
        
        state["optimized_routes"] = optimized_routes
        state["final_recommendation"] = final_recommendation
        state["processing_complete"] = True
        state["current_step"] = "optimization_complete"
        state["messages"].append(
            AIMessage(content=f"Optimization complete. {len(top_routes)} routes recommended.")
        )
        
        return state
    
    async def optimize_routes(self, task_id: str, upload_data, information_analysis: Dict[str, Any], 
                            locations: List[Dict], task_storage) -> Dict[str, Any]:
        """Run the complete route optimization workflow"""
        config = {"configurable": {"thread_id": f"route_{task_id}"}}
        initial_state = {
            "messages": [HumanMessage(content=f"Optimize routes for {len(upload_data.device_forecasts)} forecasts")],
            "upload_data": upload_data.dict(),
            "information_analysis": information_analysis,
            "locations": locations,
            "candidate_routes": [],
            "optimized_routes": [],
            "final_recommendation": {},
            "processing_complete": False,
            "current_step": "starting"
        }
        
        final_result = None
        async for state in self.workflow.astream(initial_state, config=config):
            final_result = state
            # Update task status with current step
            for node_name, node_state in state.items():
                if node_name != "__end__":
                    task_storage.update_task(task_id, {
                        "current_step": f"route_agent_{node_state.get('current_step', 'processing')}"
                    })
        
        # Extract final results
        final_state = final_result.get("optimization", final_result)
        return {
            "optimized_routes": final_state.get("optimized_routes", []),
            "final_recommendation": final_state.get("final_recommendation", {})
        }
    
    async def test_workflow(self, upload_data, info_analysis: Dict[str, Any], locations: List[Dict]) -> Dict[str, Any]:
        """Test the workflow independently"""
        test_config = {"configurable": {"thread_id": f"test_route_{uuid.uuid4()}"}}
        initial_state = {
            "messages": [HumanMessage(content="Test route optimization")],
            "upload_data": upload_data.dict(),
            "information_analysis": info_analysis,
            "locations": locations,
            "candidate_routes": [],
            "optimized_routes": [],
            "final_recommendation": {},
            "processing_complete": False,
            "current_step": "starting"
        }
        
        final_result = {}
        async for state in self.workflow.astream(initial_state, config=test_config):
            final_result = state
        
        return {
            "final_state": final_result.get("optimization", final_result),
            "messages": [msg.content for msg in final_result.get("optimization", {}).get("messages", [])]
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information for debugging"""
        try:
            graph_dict = self.workflow.get_graph().to_json()
            return {
                "workflow_type": "Route Planning Agent",
                "graph_structure": graph_dict,
                "nodes": ["route_generation", "cost_analysis", "risk_assessment", "optimization"],
                "description": "Generates and optimizes supply chain routes"
            }
        except Exception as e:
            return {"error": str(e)}