def fix_route_data_for_storage(route_data):
    """Fix route data to ensure it can be stored properly"""
    try:
        # Ensure all points have proper location structure
        if "points" in route_data:
            fixed_points = []
            for point in route_data["points"]:
                if isinstance(point, dict):
                    # Ensure location has required fields
                    location = point.get("location", {})
                    
                    # Add missing required fields
                    if not location.get("id"):
                        location["id"] = f"waypoint_{point.get('order', 1)}"
                    if not location.get("type"):
                        location["type"] = point.get("waypoint_type", "waypoint")
                    if not location.get("name"):
                        location["name"] = f"Waypoint {point.get('order', 1)}"
                    if not location.get("lat"):
                        location["lat"] = 0.0
                    if not location.get("lng"):
                        location["lng"] = 0.0
                    
                    # Create fixed point
                    fixed_point = {
                        "location": location,
                        "order": point.get("order", 1),
                        "estimated_arrival": point.get("estimated_arrival")
                    }
                    fixed_points.append(fixed_point)
            
            route_data["points"] = fixed_points
        
        return route_data
    except Exception as e:
        print(f"Error fixing route data: {e}")
        return route_data