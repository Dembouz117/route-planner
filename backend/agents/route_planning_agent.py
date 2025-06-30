import uuid
import json
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from datetime import datetime
from models.schemas import RoutePlanningState
from tools.route_planning_tools import (
    calculate_route_distance,
    estimate_shipping_costs,
    optimize_route_selection,
    generate_route_waypoints
)
from utils.routes import fix_route_data_for_storage

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
        """Create the Route Planning Agent workflow with proper ReAct pattern"""
        workflow = StateGraph(RoutePlanningState)
        
        # Add nodes
        workflow.add_node("react_agent", self._react_agent_node)
        workflow.add_node("check_routes", self._check_routes_node)
        workflow.add_node("finalize_routes", self._finalize_routes_node)
        
        # Add edges with loops back to agent for continued reasoning
        workflow.add_edge(START, "react_agent")
        workflow.add_conditional_edges(
            "react_agent",
            self._should_continue_planning,
            {
                "continue": "react_agent",  # Loop back for more tool usage
                "check": "check_routes"
            }
        )
        workflow.add_conditional_edges(
            "check_routes",
            self._are_routes_complete,
            {
                "continue": "react_agent",  # Loop back if more work needed
                "finalize": "finalize_routes"
            }
        )
        workflow.add_edge("finalize_routes", END)
        
        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _react_agent_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Node where Claude uses ReAct pattern to plan routes"""
        print("🚚 Route Planning Agent: Optimizing routes with Claude LLM")
        
        upload_data = state["upload_data"]
        info_analysis = state["information_analysis"]
        locations = state["locations"]
        
        # Determine what prompt to give Claude based on current state
        if not state.get("messages") or len(state["messages"]) == 0:
            # Initial route planning prompt
            route_prompt = f"""
            You are an expert supply chain route planning agent. Your task is to optimize shipping routes based on the following data:

            SUPPLY CHAIN DATA:
            - Region: {upload_data.get('region', 'Unknown')}
            - Number of forecasts: {len(upload_data.get('device_forecasts', []))}
            - Device Forecasts: {json.dumps(upload_data.get('device_forecasts', []), indent=2)}

            RISK INTELLIGENCE:
            - Overall risk level: {info_analysis.get('risk_assessment', {}).get('overall_risk', 'unknown')}
            - Key disruptions: {[d.get('title', '') for d in info_analysis.get('disruption_data', [])]}
            - Affected transport modes: {info_analysis.get('risk_assessment', {}).get('affected_transport_modes', [])}

            AVAILABLE LOCATIONS (first 10):
            {json.dumps(locations[:10], indent=2)}

            You have access to these tools:
            1. calculate_route_distance - Calculate distances between geographic points
            2. estimate_shipping_costs - Estimate costs for different transport modes and quantities
            3. generate_route_waypoints - Generate intermediate stops for complex routes
            4. optimize_route_selection - Optimize and rank multiple route candidates

            Your task:
            1. For each device forecast, identify suitable origin and destination points from the available locations
            2. Calculate distances between potential route pairs
            3. Estimate shipping costs considering risk factors and quantities
            4. Generate route waypoints for promising routes (especially long-distance ones)
            5. Create multiple route alternatives with different transport modes
            6. Optimize the final route selection based on cost, risk, and efficiency

            Consider the risk intelligence when making transport mode decisions - avoid high-risk modes when possible.
            Start by analyzing the forecasts and calculating distances for the most promising routes.
            """
        else:
            # Continuation prompt based on current progress
            candidates_count = len(state.get("candidate_routes", []))
            optimized_count = len(state.get("optimized_routes", []))
            
            route_prompt = f"""
            Continue route planning optimization.
            
            Current progress:
            - Candidate routes generated: {candidates_count}
            - Optimized routes: {optimized_count}
            - Device forecasts to process: {len(upload_data.get('device_forecasts', []))}
            
            If you haven't generated enough route alternatives, continue using the tools to:
            - Calculate more route distances
            - Estimate costs for different transport modes
            - Generate waypoints for complex routes
            - Optimize the route selection
            
            If you have sufficient routes, provide a summary of your recommendations.
            """
        
        # Create message list for the agent
        if not state.get("messages"):
            messages = [HumanMessage(content=route_prompt)]
        else:
            messages = state["messages"] + [HumanMessage(content=route_prompt)]
        
        # Invoke the ReAct agent - Claude will decide which tools to use
        agent_config = {"configurable": {"thread_id": f"route_agent_{state.get('current_step', uuid.uuid4())}"}}
        result = self.react_agent.invoke(
            {"messages": messages},
            config=agent_config
        )
        
        # Update state with new messages from the agent interaction
        state["messages"] = result["messages"]
        state["current_step"] = "agent_route_processing"
        
        # Extract any tool results and route data from the conversation
        self._extract_route_data_from_messages(state)
        
        return state
    
    def _extract_route_data_from_messages(self, state: RoutePlanningState):
        """Extract route planning results from agent messages and update state"""
        print(f"🔍 Extracting route data from {len(state['messages'])} messages")
        
        upload_data = state["upload_data"]
        info_analysis = state["information_analysis"]
        
        # Collect all tool results
        tool_results = {}
        distance_results = []
        cost_results = []
        waypoint_results = []
        
        for i, message in enumerate(state["messages"]):
            # Handle tool calls in Claude's content format
            if hasattr(message, 'content') and isinstance(message.content, list):
                for content_item in message.content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'tool_use':
                        tool_name = content_item.get('name', '')
                        tool_id = content_item.get('id', '')
                        
                        # Find the result for this tool call
                        tool_result = self._find_tool_result_by_id(state["messages"], tool_id, i)
                        
                        if tool_result:
                            print(f"🔧 Tool result found in route message: {tool_name} - {tool_result}")
                            
                            # Collect results by type
                            if tool_name == "calculate_route_distance":
                                distance_results.append(tool_result)
                            elif tool_name == "estimate_shipping_costs":
                                cost_results.append(tool_result)
                            elif tool_name == "generate_route_waypoints":
                                waypoint_results.append(tool_result)
                            elif tool_name == "optimize_route_selection":
                                if not tool_result.get('error'):
                                    state["optimized_routes"] = tool_result.get("optimized_routes", [])
                                    state["final_recommendation"] = tool_result.get("optimization_summary", {})
                                else:
                                    print(f"⚠️ Optimization tool error: {tool_result.get('error')}")
        
        # Build candidate routes from the collected tool results
        candidate_routes = self._build_routes_from_tool_collections(
            distance_results, cost_results, waypoint_results, upload_data, info_analysis
        )
        
        if candidate_routes:
            state["candidate_routes"] = candidate_routes
            print(f"✅ Built {len(candidate_routes)} candidate routes from tool results")
        
        print(f"🔍 Route state - Candidates: {len(state.get('candidate_routes', []))}, Optimized: {len(state.get('optimized_routes', []))}")
    
    def _find_tool_result_by_id(self, messages, tool_call_id, start_index):
        """Find tool result starting from a specific message index"""
        # Look in messages after the tool call
        for msg in messages[start_index:]:
            # Check for tool results in Claude's content format
            if hasattr(msg, 'content') and isinstance(msg.content, list):
                for content_item in msg.content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'tool_result':
                        if content_item.get('tool_use_id') == tool_call_id:
                            return self._parse_tool_content(content_item.get('content'))
            
            # Check for ToolMessage type
            elif hasattr(msg, 'tool_call_id') and msg.tool_call_id == tool_call_id:
                content = getattr(msg, 'content', None)
                return self._parse_tool_content(content)
        
        return None
    
    def _parse_tool_content(self, content):
        """Parse tool content to extract the actual result"""
        if isinstance(content, str):
            try:
                import json
                return json.loads(content)
            except (json.JSONDecodeError, TypeError):
                return content
        return content
    
    def _build_routes_from_tool_collections(self, distance_results, cost_results, waypoint_results, upload_data, info_analysis):
        """Build candidate routes from collections of tool results"""
        candidate_routes = []
        
        # Get forecasts
        forecasts = upload_data.get("device_forecasts", [])
        if not forecasts:
            return candidate_routes
        
        # Build routes by matching tool results to forecasts
        for i, forecast in enumerate(forecasts):
            if isinstance(forecast, dict):
                forecast_data = forecast
            else:
                forecast_data = forecast  # Assume it's already a dict from .dict() call
            
            # Try to match distance and cost results
            if i < len(distance_results) and i < len(cost_results):
                distance_result = distance_results[i]
                cost_result = cost_results[i]
                waypoints = waypoint_results[i] if i < len(waypoint_results) else None
                
                # Get risk multiplier
                risk_multiplier = 1.0 + info_analysis.get("risk_assessment", {}).get("risk_score", 0.2)
                
                # Fix waypoints to ensure proper format
                route_points = []
                if waypoints and waypoints.get("route_waypoints"):
                    for point in waypoints["route_waypoints"]:
                        # Ensure the location has required fields
                        location = point.get("location", {})
                        if not location.get("id"):
                            location["id"] = f"loc_{i}_{point.get('order', 1)}"
                        if not location.get("type"):
                            location["type"] = point.get("waypoint_type", "waypoint")
                        
                        # Create proper point structure
                        route_points.append({
                            "location": location,
                            "order": point.get("order", 1),
                            "estimated_arrival": point.get("estimated_arrival"),
                            "waypoint_type": point.get("waypoint_type", "waypoint")
                        })
                
                # Create route object
                route = {
                    "id": str(uuid.uuid4()),
                    "forecast_id": forecast_data.get("model", f"forecast_{i}"),
                    "points": route_points,
                    "total_distance": distance_result.get("distance_km", 1000),
                    "transport_mode": distance_result.get("optimal_transport_mode", "air"),
                    "quantity": forecast_data.get("quantity", 100),
                    "priority": forecast_data.get("priority", "medium"),
                    "total_cost": cost_result.get("total_cost", 1000),
                    "risk_score": min(0.2 + (risk_multiplier - 1.0), 1.0),
                    "estimated_duration": f"{waypoints.get('estimated_duration_days', 3) if waypoints else 3} days",
                    "cost_breakdown": cost_result.get("cost_breakdown", {}),
                    "risk_factors": info_analysis.get("risk_assessment", {}).get("key_concerns", [])
                }
                
                candidate_routes.append(route)
        
        # If we couldn't match 1:1, create routes from available data
        if not candidate_routes and (distance_results or cost_results):
            # Create at least one route from available data
            distance_result = distance_results[0] if distance_results else {"distance_km": 1000, "optimal_transport_mode": "air"}
            cost_result = cost_results[0] if cost_results else {"total_cost": 1000, "cost_breakdown": {}}
            waypoints = waypoint_results[0] if waypoint_results else None
            
            # Fix waypoints for this route too
            route_points = []
            if waypoints and waypoints.get("route_waypoints"):
                for point in waypoints["route_waypoints"]:
                    location = point.get("location", {})
                    if not location.get("id"):
                        location["id"] = f"combined_loc_{point.get('order', 1)}"
                    if not location.get("type"):
                        location["type"] = point.get("waypoint_type", "waypoint")
                    
                    route_points.append({
                        "location": location,
                        "order": point.get("order", 1),
                        "estimated_arrival": point.get("estimated_arrival"),
                        "waypoint_type": point.get("waypoint_type", "waypoint")
                    })
            
            route = {
                "id": str(uuid.uuid4()),
                "forecast_id": "combined_forecast",
                "points": route_points,
                "total_distance": distance_result.get("distance_km", 1000),
                "transport_mode": distance_result.get("optimal_transport_mode", "air"),
                "quantity": sum(f.get("quantity", 100) for f in forecasts),
                "priority": "medium",
                "total_cost": cost_result.get("total_cost", 1000),
                "risk_score": 0.3,
                "estimated_duration": f"{waypoints.get('estimated_duration_days', 3) if waypoints else 3} days",
                "cost_breakdown": cost_result.get("cost_breakdown", {}),
                "risk_factors": info_analysis.get("risk_assessment", {}).get("key_concerns", [])
            }
            
            candidate_routes.append(route)
        
        return candidate_routes
    
    def _find_tool_result(self, messages, tool_call_id):
        """Find tool result message corresponding to a tool call"""
        for msg in messages:
            if hasattr(msg, 'tool_call_id') and msg.tool_call_id == tool_call_id:
                try:
                    # Try to parse JSON result
                    import json
                    return json.loads(msg.content)
                except:
                    # Return raw content if not JSON
                    return msg.content
        return None
    
    def _build_routes_from_tool_results(self, tool_results, upload_data, info_analysis, locations):
        """Build candidate routes from tool calculation results"""
        candidate_routes = []
        
        # Group tool results by type
        distance_calcs = {}
        cost_estimates = {}
        waypoint_data = {}
        
        for tool_id, tool_data in tool_results.items():
            if tool_data["tool_name"] == "calculate_route_distance":
                distance_calcs[tool_id] = tool_data
            elif tool_data["tool_name"] == "estimate_shipping_costs":
                cost_estimates[tool_id] = tool_data
            elif tool_data["tool_name"] == "generate_route_waypoints":
                waypoint_data[tool_id] = tool_data
        
        # Build routes from forecasts and tool results
        for i, forecast in enumerate(upload_data.get("device_forecasts", [])):
            if isinstance(forecast, dict):
                forecast_data = forecast
            else:
                forecast_data = forecast.dict()
            
            # Find relevant tool results for this forecast
            route_distance = None
            route_cost = None
            route_waypoints = []
            
            # Use first available distance calculation
            if distance_calcs:
                route_distance = list(distance_calcs.values())[0]["result"]
            
            # Use first available cost estimate
            if cost_estimates:
                route_cost = list(cost_estimates.values())[0]["result"]
            
            # Use first available waypoint data
            if waypoint_data:
                waypoint_result = list(waypoint_data.values())[0]["result"]
                route_waypoints = waypoint_result.get("route_waypoints", [])
            
            # Create route object
            if route_distance and route_cost:
                risk_multiplier = 1.0 + info_analysis.get("risk_assessment", {}).get("risk_score", 0.2)
                
                route = {
                    "id": str(uuid.uuid4()),
                    "forecast_id": forecast_data.get("model", f"forecast_{i}"),
                    "points": route_waypoints or self._generate_basic_waypoints(locations, forecast_data),
                    "total_distance": route_distance.get("distance_km", 1000),
                    "transport_mode": route_distance.get("optimal_transport_mode", "air"),
                    "quantity": forecast_data.get("quantity", 100),
                    "priority": forecast_data.get("priority", "medium"),
                    "total_cost": route_cost.get("total_cost", 1000),
                    "risk_score": min(0.2 + (risk_multiplier - 1.0), 1.0),
                    "estimated_duration": f"{route_cost.get('estimated_days', 3)} days",
                    "cost_breakdown": route_cost.get("cost_breakdown", {}),
                    "risk_factors": info_analysis.get("risk_assessment", {}).get("key_concerns", [])
                }
                
                candidate_routes.append(route)
        
        return candidate_routes
    
    def _generate_basic_waypoints(self, locations, forecast_data):
        """Generate basic waypoints when tool didn't provide them"""
        if len(locations) < 2:
            return []
        
        origin = locations[0]  # First location as origin
        destination = locations[1]  # Second location as destination
        
        return [
            {"location": origin, "order": 1, "waypoint_type": "origin"},
            {"location": destination, "order": 2, "waypoint_type": "destination"}
        ]
    
    def _should_continue_planning(self, state: RoutePlanningState) -> Literal["continue", "check"]:
        """Determine if Claude should continue planning or move to completion check"""
        # Count current candidates and check iteration limits
        candidates_count = len(state.get("candidate_routes", []))
        optimized_count = len(state.get("optimized_routes", []))
        forecasts_count = len(state["upload_data"].get("device_forecasts", []))
        
        print(f"🔍 Planning continuation check - Candidates: {candidates_count}, Optimized: {optimized_count}, Forecasts: {forecasts_count}")
        
        # If we have enough routes, move to check
        if candidates_count >= forecasts_count or optimized_count >= 1 or candidates_count >= 3:
            print("✅ Sufficient routes generated - moving to check")
            return "check"
        
        if state.get("messages"):
            last_message = state["messages"][-1]
            
            # If Claude is still making tool calls, let it continue (with iteration limit)
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                print("🔄 Claude still making tool calls - continuing")
                return "continue"
            
            # Check if Claude's response indicates completion
            last_content = getattr(last_message, 'content', '').lower()
            if any(phrase in last_content for phrase in [
                "optimization complete", "routes finalized", "recommendations ready",
                "planning complete", "final routes", "best routes identified"
            ]):
                print("✅ Claude indicates completion - moving to check")
                return "check"
        
        print("🔄 Continuing planning")
        return "continue"
    
    def _check_routes_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Check if route planning is complete"""
        print("📊 Route Planning Agent: Checking route completeness")
        
        candidates_count = len(state.get("candidate_routes", []))
        optimized_count = len(state.get("optimized_routes", []))
        forecasts_count = len(state["upload_data"].get("device_forecasts", []))
        
        state["current_step"] = f"checking_routes_c{candidates_count}_o{optimized_count}_f{forecasts_count}"
        
        return state
    
    def _are_routes_complete(self, state: RoutePlanningState) -> Literal["continue", "finalize"]:
        """Determine if we have sufficient routes or need more planning"""
        candidates_count = len(state.get("candidate_routes", []))
        optimized_count = len(state.get("optimized_routes", []))
        forecasts_count = len(state["upload_data"].get("device_forecasts", []))
        
        print(f"🔍 Route completion check - Candidates: {candidates_count}, Optimized: {optimized_count}, Forecasts: {forecasts_count}")
        
        # Consider complete if we have at least one route per forecast or some optimized routes
        # Or if we have reasonable candidate routes
        if candidates_count >= forecasts_count or optimized_count >= 1 or candidates_count >= 3:
            print("✅ Routes are complete - proceeding to finalize")
            return "finalize"
        
        print("⏳ Need more routes - continuing")
        return "continue"
    
    def _finalize_routes_node(self, state: RoutePlanningState) -> RoutePlanningState:
        """Finalize route recommendations"""
        print("✅ Route Planning Agent: Finalizing route recommendations")
        
        candidate_routes = state.get("candidate_routes", [])
        optimized_routes = state.get("optimized_routes", [])
        
        print(f"🔍 Finalizing with - Candidates: {len(candidate_routes)}, Optimized: {len(optimized_routes)}")
        
        # If we have candidates but no optimized routes, try to optimize them now
        if candidate_routes and not optimized_routes:
            print("🔧 Running final optimization on candidate routes")
            try:
                import json
                from tools.route_planning_tools import optimize_route_selection
                
                optimization_result = optimize_route_selection.invoke({
                    "candidate_routes_json": json.dumps(candidate_routes)
                })
                
                if not optimization_result.get('error'):
                    optimized_routes = optimization_result.get("optimized_routes", candidate_routes)
                    state["optimized_routes"] = optimized_routes
                    print(f"✅ Final optimization produced {len(optimized_routes)} routes")
                else:
                    print(f"⚠️ Final optimization failed: {optimization_result.get('error')}")
                    optimized_routes = candidate_routes  # Use candidates as fallback
                    state["optimized_routes"] = optimized_routes
            except Exception as e:
                print(f"⚠️ Final optimization error: {e}")
                optimized_routes = candidate_routes  # Use candidates as fallback
                state["optimized_routes"] = optimized_routes
        
        # If still no routes, use candidates
        if not optimized_routes and candidate_routes:
            optimized_routes = fix_route_data_for_storage(candidate_routes)
            state["optimized_routes"] = optimized_routes
        
        # Create final recommendation
        final_recommendation = {
            "recommended_routes": optimized_routes[:3] if optimized_routes else [],
            "total_routes_analyzed": len(optimized_routes),
            "average_cost": round(sum(r.get("total_cost", 0) for r in optimized_routes) / max(len(optimized_routes), 1), 2) if optimized_routes else 0,
            "average_risk": round(sum(r.get("risk_score", 0) for r in optimized_routes) / max(len(optimized_routes), 1), 2) if optimized_routes else 0,
            "optimization_timestamp": datetime.now().isoformat(),
            "risk_factors_considered": state["information_analysis"].get("risk_assessment", {}).get("risk_factors", []),
            "llm_reasoning": "Claude LLM used for intelligent route planning and tool orchestration"
        }
        
        state["final_recommendation"] = final_recommendation
        state["processing_complete"] = True
        state["current_step"] = "optimization_complete"
        
        # Add summary message
        summary = f"""Route optimization complete:
        - Generated {len(candidate_routes)} candidate routes
        - Recommended {len(final_recommendation['recommended_routes'])} optimal routes
        - Average cost: ${final_recommendation['average_cost']:.2f}
        - Risk level: {state['information_analysis'].get('risk_assessment', {}).get('overall_risk', 'unknown')}"""
        
        state["messages"].append(AIMessage(content=summary))
        
        print(f"🎯 Final recommendation: {len(final_recommendation['recommended_routes'])} routes")
        return state
    
    async def optimize_routes(self, task_id: str, upload_data, information_analysis: Dict[str, Any], 
                            locations: List[Dict], task_storage) -> Dict[str, Any]:
        """Run the complete route optimization workflow"""
        config = {"configurable": {"thread_id": f"route_{task_id}"}, "recursion_limit": 20}
        initial_state = {
            "messages": [],
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
            # Update task status
            for node_name, node_state in state.items():
                if node_name != "__end__":
                    current_step = node_state.get('current_step', 'processing')
                    progress = 70 if "checking" in current_step else 80 if "processing" in current_step else 90
                    task_storage.update_task(task_id, {
                        "current_step": f"route_agent_{current_step}",
                        "progress": progress
                    })
        
        final_state = final_result.get("finalize_routes", final_result)
        if not final_state:
            final_state = list(final_result.values())[-1] if final_result else {}
        
        return {
            "optimized_routes": final_state.get("optimized_routes", []),
            "final_recommendation": final_state.get("final_recommendation", {}),
            "llm_reasoning": [msg.content for msg in final_state.get("messages", []) if isinstance(msg, AIMessage)]
        }
    
    async def test_workflow(self, upload_data, info_analysis: Dict[str, Any], locations: List[Dict]) -> Dict[str, Any]:
        """Test the workflow independently"""
        test_config = {"configurable": {"thread_id": f"test_route_{uuid.uuid4()}"}, "recursion_limit": 20}
        initial_state = {
            "messages": [],
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
        
        final_state = final_result.get("finalize_routes", final_result)
        if not final_state:
            final_state = list(final_result.values())[-1] if final_result else {}
        
        return {
            "final_state": final_state,
            "agent_messages": [msg.content for msg in final_state.get("messages", [])],
            "llm_reasoning": "Claude LLM used for intelligent route planning and decision making"
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get workflow information for debugging"""
        try:
            graph_dict = self.workflow.get_graph().to_json()
            return {
                "workflow_type": "Route Planning Agent with Claude LLM ReAct",
                "llm_model": "claude-3-5-sonnet-20241022",
                "agent_type": "ReAct Agent with Looping",
                "tools_available": [tool.name for tool in self.tools],
                "graph_structure": graph_dict,
                "nodes": ["react_agent", "check_routes", "finalize_routes"],
                "description": "LLM decides which tools to use for route optimization with loops for continued reasoning"
            }
        except Exception as e:
            return {"error": str(e)}