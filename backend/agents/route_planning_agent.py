import uuid
import json
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from datetime import datetime
from models.schemas import RoutePlanningState, OptimizedRoute, RoutePoint, LocationPoint
from tools.route_planning_tools import (
    calculate_route_distance,
    estimate_shipping_costs,
    optimize_route_selection,
    generate_route_waypoints
)

class RoutePlanningAgent:
    def __init__(self, anthropic_api_key: str):
        # Initialize Claude LLM
        self.llm = ChatAnthropic(
            api_key=anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_tokens=4000
        )
        
        # Define tools for the agent
        self.tools = [
            calculate_route_distance,
            estimate_shipping_costs,
            optimize_route_selection,
            generate_route_waypoints
        ]
        
        # Create ReAct agent with Claude and tools
        self.react_agent = create_react_agent(self.llm, self.tools)
        
        # Create the main workflow
        self.workflow = self._create_workflow()
    
    def _create_workflow(self):
        """Create the Route Planning Agent workflow using ReAct pattern"""
        workflow = StateGraph(RoutePlanningState)
        
        # Add nodes
        workflow.add_node("route_agent", self._agent_node)
        workflow.add_node("finalize_routes", self._finalize_routes_node)
        
        # Add edges
        workflow.add_edge(START, "route_agent")
        workflow.add_edge("route_agent", "finalize_routes")
        workflow.add_edge("finalize_routes", END)
        
        # Compile with memory only
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _agent_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node where the ReAct agent processes route optimization request"""
        print("🚚 Route Planning Agent: Optimizing routes with Claude LLM")
        
        upload_data = state["upload_data"]
        info_analysis = state["information_analysis"]
        locations = state["locations"]
        
        # Create comprehensive prompt for the agent
        route_prompt = f"""
        You are an expert supply chain route planning agent. Your task is to optimize shipping routes.
        
        UPLOAD DATA SUMMARY:
        - Region: {upload_data.get('region', 'Unknown')}
        - Number of forecasts: {len(upload_data.get('device_forecasts', []))}
        - Forecasts: {json.dumps(upload_data.get('device_forecasts', []), indent=2)}
        
        AVAILABLE LOCATIONS:
        {json.dumps(locations[:10], indent=2)}  # Show first 10 locations
        
        RISK INTELLIGENCE:
        - Overall risk level: {info_analysis.get('risk_assessment', {}).get('overall_risk', 'unknown')}
        - Key disruptions: {info_analysis.get('disruption_data', [])}
        
        YOUR TASKS:
        1. For each device forecast, calculate distances between suitable origin and destination points
        2. Estimate shipping costs considering the risk factors from the intelligence analysis
        3. Generate route waypoints for the most promising routes
        4. Optimize the final route selection based on cost, risk, and efficiency
        
        Use the available tools systematically to create the best possible route recommendations.
        Consider the risk intelligence when making transport mode decisions.
        """
        
        # Invoke the ReAct agent
        agent_config = {"configurable": {"thread_id": f"route_agent_{uuid.uuid4()}"}}
        result = self.react_agent.invoke(
            {"messages": [HumanMessage(content=route_prompt)]},
            config=agent_config
        )
        
        # Extract the agent's response
        if result and "messages" in result:
            agent_response = result["messages"][-1].content if result["messages"] else "Route analysis completed"
        else:
            agent_response = "Route planning agent processing completed"
        
        # Update state with agent's work
        state["messages"].extend([
            HumanMessage(content=route_prompt),
            AIMessage(content=agent_response)
        ])
        state["current_step"] = "agent_route_analysis_complete"
        
        return state
    
    def _finalize_routes_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node to finalize route recommendations and create structured output"""
        print("🎯 Route Planning Agent: Finalizing route recommendations")
        
        # Generate candidate routes if the agent didn't create them
        candidate_routes = self._generate_candidate_routes(state)
        print("Candidate routes generated:", len(candidate_routes))
        # Optimize routes using the tool
        if candidate_routes:
            print("Optimizing candidate routes...")
            optimization_result = optimize_route_selection.invoke({
                "candidate_routes_json": json.dumps(candidate_routes)
            })
            print("Optimization result:", optimization_result)
            
            optimized_routes = optimization_result.get("optimized_routes", candidate_routes)
            recommended_routes = optimization_result.get("recommended_routes", optimized_routes[:3])
        else:
            optimized_routes = []
            recommended_routes = []
        
        # Create final recommendation
        final_recommendation = {
            "recommended_routes": recommended_routes,
            "total_routes_analyzed": len(optimized_routes),
            "average_cost": round(sum(r.get("total_cost", 0) for r in optimized_routes) / max(len(optimized_routes), 1), 2),
            "average_risk": round(sum(r.get("risk_score", 0) for r in optimized_routes) / max(len(optimized_routes), 1), 2),
            "optimization_timestamp": datetime.now().isoformat(),
            "risk_factors_considered": state["information_analysis"].get("risk_assessment", {}).get("risk_factors", []),
            "llm_reasoning": "Claude LLM used for intelligent route planning and optimization"
        }
        
        # Update state with final results
        state["candidate_routes"] = candidate_routes
        state["optimized_routes"] = optimized_routes
        state["final_recommendation"] = final_recommendation
        state["processing_complete"] = True
        state["current_step"] = "optimization_complete"
        
        # Add summary message
        summary = f"""Route optimization complete:
        - Generated {len(candidate_routes)} candidate routes
        - Recommended {len(recommended_routes)} optimal routes
        - Average cost: ${final_recommendation['average_cost']:.2f}
        - Risk level incorporated: {state['information_analysis'].get('risk_assessment', {}).get('overall_risk', 'unknown')}"""
        
        state["messages"].append(AIMessage(content=summary))
        
        return state
    
    def _generate_candidate_routes(self, state: RoutePlanningState) -> List[Dict[str, Any]]:
        """Generate candidate routes for optimization"""
        upload_data = state["upload_data"]
        locations = state["locations"]
        info_analysis = state["information_analysis"]
        
        candidate_routes = []
        
        # Get risk multiplier from information analysis
        risk_level = info_analysis.get("risk_assessment", {}).get("overall_risk", "low")
        risk_multiplier = {"low": 1.0, "medium": 1.3, "high": 1.6}.get(risk_level, 1.0)
        
        for forecast in upload_data.get("device_forecasts", []):
            destination = forecast.get("destination", "").lower() if isinstance(forecast, dict) else forecast.destination.lower()
            
            # Find suitable origin and destination points
            origin_candidates = [loc for loc in locations if "singapore" in loc["name"].lower() or "hub" in loc["name"].lower()]
            dest_candidates = [loc for loc in locations if destination in loc["name"].lower()]
            
            # Fallback to first available locations
            if not origin_candidates:
                origin_candidates = locations[:1]
            if not dest_candidates:
                dest_candidates = locations[1:2] if len(locations) > 1 else locations[:1]
            
            if not origin_candidates or not dest_candidates:
                continue
                
            origin = origin_candidates[0]
            destination_loc = dest_candidates[0]
            
            # Calculate distance using tool
            try:
                distance_result = calculate_route_distance.invoke({
                    "origin_lat": origin["lat"],
                    "origin_lng": origin["lng"], 
                    "dest_lat": destination_loc["lat"],
                    "dest_lng": destination_loc["lng"]
                })
                distance = distance_result["distance_km"]
                optimal_transport = distance_result["optimal_transport_mode"]
            except Exception as e:
                print(f"Distance calculation failed: {e}")
                # Fallback calculation
                distance = 1000.0
                optimal_transport = "air"
            
            # Generate route variants with different transport modes
            transport_modes = ["air", "sea", "land"] if distance > 500 else ["land", "air"]
            
            for transport_mode in transport_modes:
                # Generate waypoints using tool
                waypoints_result = generate_route_waypoints.invoke({
                    "origin_location": json.dumps(origin),
                    "destination_location": json.dumps(destination_loc),
                    "transport_mode": transport_mode
                })
                
                # Estimate costs using tool
                cost_result = estimate_shipping_costs.invoke({
                    "distance_km": distance,
                    "transport_mode": transport_mode,
                    "quantity": forecast["quantity"],
                    "risk_multiplier": risk_multiplier
                })
                
                # Calculate risk score based on disruptions
                risk_score = self._calculate_risk_score(transport_mode, info_analysis, distance)
                
                # Create route object
                route = {
                    "id": str(uuid.uuid4()),
                    "forecast_id": forecast.get("model", "unknown") if isinstance(forecast, dict) else forecast.model,
                    "points": waypoints_result.get("route_waypoints", []),
                    "total_distance": distance,
                    "transport_mode": transport_mode,
                    "quantity": forecast.get("quantity", 0) if isinstance(forecast, dict) else forecast.quantity,
                    "priority": forecast.get("priority", "medium") if isinstance(forecast, dict) else forecast.priority,
                    "total_cost": cost_result["total_cost"],
                    "risk_score": risk_score,
                    "estimated_duration": f"{waypoints_result.get('estimated_duration_days', 1)} days",
                    "cost_breakdown": cost_result.get("cost_breakdown", {}),
                    "risk_factors": info_analysis.get("risk_assessment", {}).get("risk_factors", [])
                }
                
                candidate_routes.append(route)
        
        return candidate_routes
    
    def _calculate_risk_score(self, transport_mode: str, info_analysis: Dict, distance: float) -> float:
        """Calculate risk score based on transport mode and disruption intelligence"""
        base_risk = 0.2
        risk_score = base_risk
        
        # Increase risk based on disruption intelligence
        for disruption in info_analysis.get("disruption_data", []):
            disruption_title = disruption.get("title", "").lower()
            transport_modes = disruption.get("transport_modes", [])
            
            if transport_mode in transport_modes:
                impact_level = disruption.get("impact_level", "medium")
                if impact_level == "high":
                    risk_score += 0.3
                elif impact_level == "medium":
                    risk_score += 0.2
                else:
                    risk_score += 0.1
        
        # Increase risk for longer routes
        if distance > 5000:
            risk_score += 0.1
        elif distance > 2000:
            risk_score += 0.05
        
        return min(round(risk_score, 2), 1.0)
    
    async def optimize_routes(self, task_id: str, upload_data, information_analysis: Dict[str, Any], 
                            locations: List[Dict], task_storage) -> Dict[str, Any]:
        """Run the complete route optimization workflow with LLM reasoning"""
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
                    current_step = node_state.get('current_step', 'processing')
                    task_storage.update_task(task_id, {
                        "current_step": f"route_agent_{current_step}",
                        "progress": 70 if current_step == "agent_route_analysis_complete" else 90
                    })
        
        # Extract final results
        final_state = final_result.get("finalize_routes", final_result)
        return {
            "optimized_routes": final_state.get("optimized_routes", []),
            "final_recommendation": final_state.get("final_recommendation", {}),
            "llm_reasoning": [msg.content for msg in final_state.get("messages", []) if isinstance(msg, AIMessage)]
        }
    
    async def test_workflow(self, upload_data, info_analysis: Dict[str, Any], locations: List[Dict]) -> Dict[str, Any]:
        """Test the workflow independently"""
        test_config = {"configurable": {"thread_id": f"test_route_{uuid.uuid4()}"}, "recursion_limit": 10}
        initial_state = {
            "messages": [HumanMessage(content="Test route optimization with Claude LLM")],
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
            "final_state": final_result.get("finalize_routes", final_result),
            "agent_messages": [msg.content for msg in final_result.get("finalize_routes", {}).get("messages", [])],
            "llm_reasoning": "Claude LLM used for intelligent route planning and decision making"
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information for debugging"""
        try:
            graph_dict = self.workflow.get_graph().to_json()
            return {
                "workflow_type": "Route Planning Agent with Claude LLM",
                "llm_model": "claude-3-sonnet-20240229",
                "agent_type": "ReAct Agent",
                "tools_available": [tool.name for tool in self.tools],
                "graph_structure": graph_dict,
                "nodes": ["route_agent", "finalize_routes"],
                "description": "LLM-powered agent that uses tools to generate and optimize supply chain routes"
            }
        except Exception as e:
            return {"error": str(e)}