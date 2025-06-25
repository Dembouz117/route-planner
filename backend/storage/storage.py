from typing import Dict, Any, List, Optional
from models.schemas import OptimizedRoute

class TaskStorage:
    def __init__(self):
        self.tasks = {}
    
    def create_task(self, task_id: str, task_data: Dict[str, Any]):
        """Create a new task"""
        self.tasks[task_id] = task_data
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update task data"""
        if task_id in self.tasks:
            self.tasks[task_id].update(updates)
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        return list(self.tasks.values())

class RouteStorage:
    def __init__(self):
        self.routes = {}
    
    def store_route(self, route_id: str, route: OptimizedRoute):
        """Store a route"""
        self.routes[route_id] = route
    
    def get_route(self, route_id: str) -> Optional[OptimizedRoute]:
        """Get route by ID"""
        return self.routes.get(route_id)
    
    def get_all_routes(self) -> List[OptimizedRoute]:
        """Get all routes"""
        return list(self.routes.values())
    
    def approve_route(self, route_id: str):
        """Approve a route"""
        if route_id in self.routes:
            self.routes[route_id].status = "approved"

class UploadStorage:
    def __init__(self):
        self.uploads = {}
    
    def store_upload(self, upload_id: str, upload_data: Dict[str, Any]):
        """Store upload data"""
        self.uploads[upload_id] = upload_data
    
    def get_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Get upload by ID"""
        return self.uploads.get(upload_id)
    
    def get_all_uploads(self) -> List[Dict[str, Any]]:
        """Get all uploads"""
        return list(self.uploads.values())