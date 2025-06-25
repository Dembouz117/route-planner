import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Annotated
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import aiofiles

# Import organized modules
from agents.information_agent import InformationAgent
from agents.route_planning_agent import RoutePlanningAgent
from models.schemas import (
    LocationPoint, DeviceForecast, UploadData, RoutePoint, 
    OptimizedRoute, AgentResult, InformationAgentState, RoutePlanningState
)
from services.external_clients import MockPineconeClient, MockTavilyClient
from config.settings import MOCK_LOCATIONS
from utils.storage import TaskStorage, RouteStorage, UploadStorage

# Initialize external service clients
pinecone_client = MockPineconeClient()
tavily_client = MockTavilyClient()

# Initialize storage systems
task_storage = TaskStorage()
route_storage = RouteStorage()
upload_storage = UploadStorage()

# Initialize agents
information_agent = InformationAgent(pinecone_client, tavily_client)
route_planning_agent = RoutePlanningAgent()

# FastAPI app
app = FastAPI(title="Supply Chain RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task to process uploaded data using LangGraph agents
async def process_supply_chain_data(task_id: str, upload_data: UploadData):
    """Background task to process uploaded data through LangGraph agents"""
    
    try:
        # Update task status
        task_storage.update_task(task_id, {"status": "processing", "current_step": "information_analysis"})
        
        print(f"🚀 Starting multi-agent processing for task {task_id}")
        
        # Step 1: Information Agent Analysis using LangGraph
        print("🤖 Running Information Agent...")
        
        # Prepare locations data for route planning
        all_locations = []
        for location_type, locations in MOCK_LOCATIONS.items():
            for loc in locations:
                all_locations.append(loc.dict())
        
        # Run Information Agent workflow
        info_analysis = await information_agent.analyze_supply_chain(
            task_id=task_id,
            query=f"supply chain optimization {upload_data.region}",
            region=upload_data.region,
            task_storage=task_storage
        )
        
        task_storage.update_task(task_id, {
            "info_analysis": info_analysis,
            "current_step": "route_optimization"
        })
        
        print("✅ Information Agent completed")
        print(f"📊 Found {len(info_analysis['domain_knowledge'])} knowledge entries")
        print(f"⚠️ Found {len(info_analysis['disruption_data'])} disruptions")
        print(f"🎯 Risk level: {info_analysis['risk_assessment'].get('overall_risk', 'unknown')}")
        
        # Step 2: Route Planning Agent using LangGraph
        print("🚚 Running Route Planning Agent...")
        
        # Run Route Planning Agent workflow
        route_results = await route_planning_agent.optimize_routes(
            task_id=task_id,
            upload_data=upload_data,
            information_analysis=info_analysis,
            locations=all_locations,
            task_storage=task_storage
        )
        
        # Store generated routes
        route_objects = []
        for route_data in route_results["optimized_routes"]:
            route_obj = OptimizedRoute.from_dict(route_data)
            route_objects.append(route_obj)
            route_storage.store_route(route_obj.id, route_obj)
        
        task_storage.update_task(task_id, {
            "status": "completed",
            "routes": [route.dict() for route in route_objects],
            "final_recommendation": route_results["final_recommendation"],
            "completed_at": datetime.now().isoformat()
        })
        
        print("✅ Route Planning Agent completed")
        print(f"🛣️ Generated {len(route_results['optimized_routes'])} optimized routes")
        print(f"🎯 Recommended {len(route_results['final_recommendation'].get('recommended_routes', []))} top routes")
        print(f"✨ Multi-agent processing completed for task {task_id}")
        
    except Exception as e:
        print(f"❌ Error in multi-agent processing: {str(e)}")
        task_storage.update_task(task_id, {
            "status": "failed",
            "error": str(e)
        })

# API Endpoints
@app.get("/api/v1")
async def root():
    return {"message": "Supply Chain RAG API", "status": "running"}

@app.post("/api/v1/data/upload")
async def upload_data(background_tasks: BackgroundTasks, upload_data: UploadData):
    """Upload regional supply chain data and trigger agent processing"""
    
    task_id = str(uuid.uuid4())
    upload_id = str(uuid.uuid4())
    
    # Store upload data
    upload_storage.store_upload(upload_id, {
        "id": upload_id,
        "data": upload_data.dict(),
        "uploaded_at": datetime.now().isoformat(),
        "status": "uploaded"
    })
    
    # Initialize task tracking
    task_storage.create_task(task_id, {
        "id": task_id,
        "upload_id": upload_id,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "current_step": "queued"
    })
    
    # Start background processing
    background_tasks.add_task(process_supply_chain_data, task_id, upload_data)
    
    return {
        "message": "Data uploaded successfully",
        "task_id": task_id,
        "upload_id": upload_id,
        "status": "processing"
    }

@app.get("/api/v1/agents/status/{task_id}")
async def get_task_status(task_id: str):
    """Get agent task status and results"""
    task = task_storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/v1/routes")
async def get_routes():
    """Get all generated routes"""
    routes = route_storage.get_all_routes()
    return {
        "routes": [route.dict() for route in routes],
        "total": len(routes)
    }

@app.get("/api/v1/routes/{route_id}")
async def get_route(route_id: str):
    """Get specific route details"""
    route = route_storage.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route.dict()

@app.post("/api/v1/routes/{route_id}/approve")
async def approve_route(route_id: str):
    """Approve a route (Human-in-the-Loop)"""
    route = route_storage.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    # Update route status
    route_storage.approve_route(route_id)
    
    return {
        "message": "Route approved successfully",
        "route_id": route_id,
        "status": "approved"
    }

@app.get("/api/v1/locations")
async def get_locations():
    """Get all available locations for mapping"""
    return MOCK_LOCATIONS

@app.get("/api/v1/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    """Search Dell knowledge base"""
    results = pinecone_client.query(query, top_k=limit)
    return {
        "query": query,
        "results": results,
        "total": len(results)
    }

@app.get("/api/v1/agents/workflows/info")
async def get_info_agent_workflow():
    """Get Information Agent workflow definition for debugging"""
    try:
        return information_agent.get_workflow_info()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/v1/agents/workflows/route")
async def get_route_agent_workflow():
    """Get Route Planning Agent workflow definition for debugging"""
    try:
        return route_planning_agent.get_workflow_info()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/v1/agents/test/info")
async def test_information_agent(query: str = "supply chain APAC", region: str = "APAC"):
    """Test Information Agent workflow independently"""
    try:
        result = await information_agent.test_workflow(query, region)
        return {
            "test_type": "Information Agent",
            "status": "completed",
            "result": result
        }
    except Exception as e:
        return {
            "test_type": "Information Agent", 
            "status": "failed",
            "error": str(e)
        }

@app.post("/api/v1/agents/test/route")
async def test_route_planning_agent():
    """Test Route Planning Agent workflow independently"""
    try:
        # Create test data
        test_upload = UploadData(
            region="APAC",
            forecast_date="2025-Q2",
            device_forecasts=[
                DeviceForecast(
                    model="Dell Latitude 7440",
                    quantity=1000,
                    destination="Singapore",
                    priority="high",
                    delivery_window="2025-07-01 to 2025-07-31"
                )
            ],
            constraints={"max_cost_per_unit": 50}
        )
        
        # Prepare locations
        all_locations = []
        for location_type, locations in MOCK_LOCATIONS.items():
            for loc in locations:
                all_locations.append(loc.dict())
        
        # Mock info analysis
        mock_info_analysis = {
            "domain_knowledge": [{"content": "Test knowledge", "relevance_score": 0.9}],
            "disruption_data": [{"title": "Test disruption", "summary": "Test disruption content"}],
            "risk_assessment": {"overall_risk": "medium"}
        }
        
        result = await route_planning_agent.test_workflow(
            test_upload, mock_info_analysis, all_locations
        )
        
        return {
            "test_type": "Route Planning Agent",
            "status": "completed", 
            "result": result
        }
    except Exception as e:
        return {
            "test_type": "Route Planning Agent",
            "status": "failed",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
