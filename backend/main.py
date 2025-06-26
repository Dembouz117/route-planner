# Load environment variables first, before any other imports
from dotenv import load_dotenv
import os

# Load .env file from multiple possible locations
env_loaded = False
env_paths = [".env", "backend/.env", "../.env"]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"✅ Loaded .env from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("⚠️ No .env file found, using system environment variables")

# Verify API key is loaded
anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"Anthropic API Key loaded: {anthropic_key is not None}")
if anthropic_key:
    print(f"API Key preview: {anthropic_key[:10]}...")

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import json
from datetime import datetime

# Import the corrected agents with LLM integration
from agents.information_agent import InformationAgent
from agents.route_planning_agent import RoutePlanningAgent
from config.llm_config import llm_config
from models.schemas import UploadData, OptimizedRoute
from storage.storage import TaskStorage, RouteStorage, UploadStorage
from config.settings import MOCK_LOCATIONS

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent RAG Supply Chain Application",
    description="LLM-powered supply chain route optimization with real-time intelligence",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage systems
task_storage = TaskStorage()
route_storage = RouteStorage()
upload_storage = UploadStorage()

# Initialize agents with Claude LLM
try:
    information_agent = InformationAgent(llm_config.anthropic_api_key)
    route_planning_agent = RoutePlanningAgent(llm_config.anthropic_api_key)
    print("✅ Agents initialized successfully with Claude LLM")
except Exception as e:
    print(f"❌ Failed to initialize agents: {e}")
    information_agent = None
    route_planning_agent = None

# Request/Response Models
class AnalysisRequest(BaseModel):
    query: str
    region: str

class TaskResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = 0
    current_step: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class RouteApprovalRequest(BaseModel):
    approved: bool
    comments: Optional[str] = None

# API Endpoints

@app.get("/api/v1")
async def root():
    """Health check endpoint"""
    agent_status = {
        "information_agent": information_agent is not None,
        "route_planning_agent": route_planning_agent is not None,
        "llm_model": "claude-3-sonnet-20240229"
    }
    
    return {
        "message": "Multi-Agent RAG Supply Chain Application",
        "status": "running",
        "agents": agent_status,
        "llm_integration": "Claude by Anthropic"
    }

@app.get("/api/v1/agent-info")
async def get_agent_info():
    """Get information about the agents and their LLM configuration"""
    if not information_agent or not route_planning_agent:
        raise HTTPException(status_code=500, detail="Agents not properly initialized")
    
    return {
        "information_agent": information_agent.get_workflow_info(),
        "route_planning_agent": route_planning_agent.get_workflow_info(),
        "llm_config": {
            "model": "claude-3-sonnet-20240229",
            "provider": "Anthropic",
            "temperature": 0.1,
            "max_tokens": 4000
        }
    }

@app.post("/api/v1/data/upload", response_model=TaskResponse)
async def upload_data(background_tasks: BackgroundTasks, upload_data: UploadData, enable_scenario: bool = False):
    """Upload regional supply chain data and trigger agent analysis"""
    if not information_agent or not route_planning_agent:
        raise HTTPException(status_code=500, detail="Agents not properly initialized")
    
    task_id = str(uuid.uuid4())
    upload_id = str(uuid.uuid4())
    
    # Store upload data
    upload_storage.store_upload(upload_id, {
        "id": upload_id,
        "data": upload_data.dict(),
        "uploaded_at": datetime.now().isoformat(),
        "status": "processing",
        "scenario_enabled": enable_scenario
    })
    
    # Create task
    task_storage.create_task(task_id, {
        "task_id": task_id,
        "upload_id": upload_id,
        "status": "processing",
        "progress": 10,
        "current_step": "upload_received",
        "created_at": datetime.now().isoformat(),
        "upload_data": upload_data.dict(),
        "scenario_enabled": enable_scenario
    })
    
    # Start background processing
    background_tasks.add_task(
        process_supply_chain_analysis,
        task_id,
        upload_data,
        upload_data.region,
        enable_scenario
    )
    
    return TaskResponse(
        task_id=task_id,
        status="processing",
        progress=10,
        current_step="upload_received"
    )

@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Get status of a processing task"""
    task = task_storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        task_id=task_id,
        status=task.get("status", "unknown"),
        progress=task.get("progress", 0),
        current_step=task.get("current_step"),
        result=task.get("result")
    )

@app.get("/api/v1/agents/status/{task_id}", response_model=TaskResponse)
async def get_agent_status(task_id: str):
    """Get status of a processing task (alternative endpoint for compatibility)"""
    return await get_task_status(task_id)

@app.post("/api/v1/agents/information/test")
async def test_information_agent(request: AnalysisRequest):
    """Test the Information Agent independently"""
    if not information_agent:
        raise HTTPException(status_code=500, detail="Information agent not initialized")
    
    try:
        result = await information_agent.test_workflow(request.query, request.region)
        return {
            "status": "success",
            "agent_type": "Information Agent",
            "test_result": result,
            "llm_used": "claude-3-sonnet-20240229"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent test failed: {str(e)}")

@app.post("/api/v1/agents/routing/test")
async def test_route_planning_agent(upload_data: UploadData):
    """Test the Route Planning Agent independently"""
    if not route_planning_agent:
        raise HTTPException(status_code=500, detail="Route planning agent not initialized")
    
    # Create mock information analysis for testing
    mock_info_analysis = {
        "risk_assessment": {"overall_risk": "medium"},
        "disruption_data": [
            {"title": "Test disruption", "impact_level": "medium", "transport_modes": ["sea"]}
        ]
    }
    
    try:
        # Get all locations for testing
        all_locations = []
        for location_type in MOCK_LOCATIONS.values():
            all_locations.extend([loc.dict() for loc in location_type])
        
        result = await route_planning_agent.test_workflow(
            upload_data, 
            mock_info_analysis, 
            all_locations
        )
        return {
            "status": "success",
            "agent_type": "Route Planning Agent",
            "test_result": result,
            "llm_used": "claude-3-sonnet-20240229"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent test failed: {str(e)}")

@app.get("/api/v1/routes")
async def get_all_routes():
    """Get all generated routes"""
    routes = route_storage.get_all_routes()
    return {
        "routes": [route.dict() for route in routes],
        "total_count": len(routes)
    }

@app.get("/api/v1/routes/{route_id}")
async def get_route(route_id: str):
    """Get specific route details"""
    route = route_storage.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return route.dict()

@app.post("/api/v1/routes/{route_id}/approve")
async def approve_route(route_id: str, approval: RouteApprovalRequest):
    """Approve or reject a route (Human-in-the-Loop)"""
    route = route_storage.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if approval.approved:
        route_storage.approve_route(route_id)
        status = "approved"
    else:
        route.status = "rejected"
        status = "rejected"
    
    return {
        "route_id": route_id,
        "status": status,
        "comments": approval.comments,
        "approved_at": datetime.now().isoformat()
    }

@app.get("/api/v1/routes/{route_id}/visualization")
async def get_route_visualization(route_id: str):
    """Get route visualization data for map display"""
    route = route_storage.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Extract coordinates for map visualization
    waypoints = []
    for point in route.points:
        waypoints.append({
            "lat": point.location.lat,
            "lng": point.location.lng,
            "name": point.location.name,
            "type": point.location.type,
            "order": point.order
        })
    
    return {
        "route_id": route_id,
        "waypoints": waypoints,
        "transport_mode": route.transport_mode,
        "total_distance": route.total_distance,
        "estimated_duration": route.estimated_duration
    }

@app.get("/api/v1/locations")
async def get_locations():
    """Get all available locations for route planning"""
    return MOCK_LOCATIONS

@app.get("/api/v1/uploads")
async def get_uploads():
    """Get all upload history"""
    uploads = upload_storage.get_all_uploads()
    return {
        "uploads": uploads,
        "total_count": len(uploads)
    }

# Background task for processing supply chain analysis
async def process_supply_chain_analysis(task_id: str, upload_data: UploadData, region: str, enable_scenario: bool = False):
    """Background task that orchestrates both agents with LLM reasoning"""
    try:
        # Update task status
        task_storage.update_task(task_id, {
            "status": "processing",
            "progress": 20,
            "current_step": "starting_analysis"
        })
        
        # Step 1: Run Information Agent only if scenario is enabled
        if enable_scenario:
            print(f"🔍 Starting Information Agent analysis for {region} (scenario enabled)")
            device_models = [forecast.model for forecast in upload_data.device_forecasts]
            query = f"supply chain analysis {region} {' '.join(device_models)}"
            
            info_result = await information_agent.analyze_supply_chain(
                task_id, query, region, task_storage
            )
            
            task_storage.update_task(task_id, {
                "progress": 60,
                "current_step": "information_agent_complete",
                "info_analysis": info_result
            })
        else:
            print(f"📋 Skipping Information Agent - scenario disabled")
            # Create empty analysis for route planning
            info_result = {
                "domain_knowledge": [],
                "disruption_data": [],
                "risk_assessment": {"overall_risk": "low", "risk_factors": []}
            }
            
            task_storage.update_task(task_id, {
                "progress": 60,
                "current_step": "information_agent_skipped"
            })
        
        # Step 2: Run Route Planning Agent with Claude LLM
        print(f"🚚 Starting Route Planning Agent optimization")
        task_storage.update_task(task_id, {
            "progress": 65,
            "current_step": "starting_route_agent"
        })
        
        # Get all locations
        all_locations = []
        for location_type in MOCK_LOCATIONS.values():
            all_locations.extend([loc.dict() for loc in location_type])
        
        route_result = await route_planning_agent.optimize_routes(
            task_id, upload_data, info_result, all_locations, task_storage
        )
        
        # Step 3: Store optimized routes
        for route_data in route_result.get("optimized_routes", []):
            try:
                optimized_route = OptimizedRoute.from_dict(route_data)
                route_storage.store_route(optimized_route.id, optimized_route)
            except Exception as e:
                print(f"Warning: Could not store route {route_data.get('id', 'unknown')}: {e}")
        
        # Step 4: Complete task
        final_result = {
            "information_analysis": info_result,
            "route_optimization": route_result,
            "routes_generated": len(route_result.get("optimized_routes", [])),
            "recommended_routes": len(route_result.get("final_recommendation", {}).get("recommended_routes", [])),
            "llm_reasoning": {
                "information_agent": info_result.get("agent_reasoning", []),
                "route_agent": route_result.get("llm_reasoning", [])
            }
        }
        
        task_storage.update_task(task_id, {
            "status": "completed",
            "progress": 100,
            "current_step": "analysis_complete",
            "result": final_result,
            "completed_at": datetime.now().isoformat()
        })
        
        print(f"✅ Task {task_id} completed successfully with Claude LLM reasoning")
        
    except Exception as e:
        print(f"❌ Task {task_id} failed: {str(e)}")
        task_storage.update_task(task_id, {
            "status": "failed",
            "progress": 0,
            "current_step": "error",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        })

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Multi-Agent RAG Supply Chain Application with Claude LLM")
    print("📋 Available endpoints:")
    print("   - POST /api/v1/data/upload - Upload supply chain data")
    print("   - GET /api/v1/tasks/{task_id} - Check task status")
    print("   - POST /api/v1/agents/information/test - Test Information Agent")
    print("   - POST /api/v1/agents/routing/test - Test Route Planning Agent")
    print("   - GET /api/v1/routes - Get all routes")
    print("   - GET /api/v1/agent-info - Get agent and LLM information")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)