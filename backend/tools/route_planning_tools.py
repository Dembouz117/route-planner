import math
import json
from typing import List, Dict, Any
from langchain_core.tools import tool

@tool
def calculate_route_distance(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> Dict[str, Any]:
    """Calculate distance between two geographic points using Haversine formula.
    
    Args:
        origin_lat: Latitude of origin point
        origin_lng: Longitude of origin point  
        dest_lat: Latitude of destination point
        dest_lng: Longitude of destination point
    
    Returns:
        Dictionary with distance in kilometers and additional metrics
    """
    # Convert to radians
    lat1, lng1, lat2, lng2 = map(math.radians, [origin_lat, origin_lng, dest_lat, dest_lng])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Earth's radius in kilometers
    
    distance_km = c * r
    
    # Determine optimal transport mode based on distance
    if distance_km < 500:
        optimal_transport = "land"
    elif distance_km < 2000:
        optimal_transport = "air"
    else:
        optimal_transport = "sea"
    
    return {
        "distance_km": round(distance_km, 2),
        "distance_miles": round(distance_km * 0.621371, 2),
        "optimal_transport_mode": optimal_transport,
        "is_long_haul": distance_km > 2000,
        "coordinates": {
            "origin": {"lat": origin_lat, "lng": origin_lng},
            "destination": {"lat": dest_lat, "lng": dest_lng}
        }
    }


@tool
def estimate_shipping_costs(distance_km: float, transport_mode: str, quantity: int, risk_multiplier: float = 1.0) -> Dict[str, Any]:
    """Estimate shipping costs based on distance, transport mode, quantity, and risk factors.
    
    Args:
        distance_km: Distance in kilometers
        transport_mode: Type of transport ('air', 'sea', 'land')
        quantity: Number of units to ship
        risk_multiplier: Risk adjustment factor (1.0 = normal, >1.0 = higher risk)
    
    Returns:
        Detailed cost breakdown and estimates
    """
    # Base cost rates per km per unit (in USD)
    base_costs = {
        "air": 2.5,      # Fastest but most expensive
        "sea": 0.3,      # Cheapest for long distances
        "land": 1.2,     # Medium cost, good for regional
        "rail": 0.8,     # Efficient for continental routes
        "multimodal": 1.0 # Combined transport modes
    }
    
    cost_per_km = base_costs.get(transport_mode.lower(), 1.0)
    
    # Calculate base cost
    base_cost = distance_km * cost_per_km * quantity * 0.01
    
    # Apply distance-based discounts for bulk shipments
    if distance_km > 5000 and quantity > 1000:
        volume_discount = 0.15  # 15% discount
    elif distance_km > 2000 and quantity > 500:
        volume_discount = 0.10  # 10% discount
    elif quantity > 100:
        volume_discount = 0.05  # 5% discount
    else:
        volume_discount = 0.0
    
    # Calculate final cost with risk adjustment
    discounted_cost = base_cost * (1 - volume_discount)
    final_cost = discounted_cost * risk_multiplier
    
    # Add fixed costs based on transport mode
    fixed_costs = {
        "air": 500,   # Airport handling fees
        "sea": 800,   # Port fees and documentation
        "land": 200,  # Border crossing and documentation
        "rail": 300,  # Terminal fees
        "multimodal": 600  # Multiple handling fees
    }
    
    handling_fee = fixed_costs.get(transport_mode.lower(), 400)
    total_cost = final_cost + handling_fee
    
    return {
        "base_cost": round(base_cost, 2),
        "volume_discount_rate": volume_discount,
        "discount_amount": round(base_cost * volume_discount, 2),
        "risk_multiplier": risk_multiplier,
        "risk_adjustment": round((discounted_cost * risk_multiplier) - discounted_cost, 2),
        "handling_fee": handling_fee,
        "total_cost": round(total_cost, 2),
        "cost_per_unit": round(total_cost / quantity, 2),
        "transport_mode": transport_mode,
        "cost_breakdown": {
            "base_shipping": round(final_cost, 2),
            "fixed_fees": handling_fee,
            "total": round(total_cost, 2)
        }
    }


@tool
def optimize_route_selection(candidate_routes_json: str) -> Dict[str, Any]:
    """Optimize and rank routes based on cost, risk, time, and other factors.
    
    Args:
        candidate_routes_json: JSON string containing list of candidate routes with their metrics
    
    Returns:
        Optimized route ranking with recommendations
    """
    try:
        candidate_routes = json.loads(candidate_routes_json)
    except (json.JSONDecodeError, TypeError):
        return {"error": "Invalid JSON format for candidate routes"}
    
    if not isinstance(candidate_routes, list) or not candidate_routes:
        return {"error": "No candidate routes provided"}
    
    # Define optimization weights
    weights = {
        "cost": 0.35,      # 35% weight on cost
        "risk": 0.25,      # 25% weight on risk
        "time": 0.20,      # 20% weight on delivery time
        "reliability": 0.20 # 20% weight on reliability
    }
    
    # Calculate scores for each route
    scored_routes = []
    
    for route in candidate_routes:
        if not isinstance(route, dict):
            continue
            
        # Extract metrics with defaults
        cost = route.get("total_cost", 1000)
        risk_score = route.get("risk_score", 0.5)
        distance = route.get("total_distance", 1000)
        transport_mode = route.get("transport_mode", "land")
        
        # Normalize cost score (lower cost = better score)
        max_cost = max([r.get("total_cost", 1000) for r in candidate_routes])
        min_cost = min([r.get("total_cost", 1000) for r in candidate_routes])
        cost_score = 1 - ((cost - min_cost) / (max_cost - min_cost)) if max_cost != min_cost else 1.0
        
        # Risk score (lower risk = better score)
        risk_score_normalized = 1 - risk_score
        
        # Time score based on transport mode and distance
        time_factors = {"air": 0.9, "sea": 0.3, "land": 0.6, "rail": 0.7, "multimodal": 0.5}
        time_score = time_factors.get(transport_mode, 0.5)
        
        # Reliability score based on transport mode
        reliability_factors = {"air": 0.8, "sea": 0.6, "land": 0.7, "rail": 0.9, "multimodal": 0.6}
        reliability_score = reliability_factors.get(transport_mode, 0.6)
        
        # Calculate composite score
        composite_score = (
            cost_score * weights["cost"] +
            risk_score_normalized * weights["risk"] +
            time_score * weights["time"] +
            reliability_score * weights["reliability"]
        )
        
        # Add calculated scores to route
        route_with_scores = route.copy()
        route_with_scores.update({
            "cost_score": round(cost_score, 3),
            "risk_score_normalized": round(risk_score_normalized, 3),
            "time_score": round(time_score, 3),
            "reliability_score": round(reliability_score, 3),
            "composite_score": round(composite_score, 3),
            "optimization_rank": 0  # Will be set after sorting
        })
        
        scored_routes.append(route_with_scores)
    
    # Sort by composite score (higher is better)
    optimized_routes = sorted(scored_routes, key=lambda x: x["composite_score"], reverse=True)
    
    # Add ranking and recommendations
    for i, route in enumerate(optimized_routes):
        route["optimization_rank"] = i + 1
        route["recommended"] = i < 3  # Top 3 routes recommended
        
        # Add specific recommendations
        if i == 0:
            route["recommendation_reason"] = "Best overall balance of cost, risk, and reliability"
        elif route["cost_score"] > 0.8:
            route["recommendation_reason"] = "Most cost-effective option"
        elif route["risk_score_normalized"] > 0.8:
            route["recommendation_reason"] = "Lowest risk alternative"
        elif route["time_score"] > 0.8:
            route["recommendation_reason"] = "Fastest delivery option"
        else:
            route["recommendation_reason"] = "Balanced alternative option"
    
    # Calculate summary statistics
    avg_cost = sum(r["total_cost"] for r in optimized_routes) / len(optimized_routes)
    avg_risk = sum(r["risk_score"] for r in optimized_routes) / len(optimized_routes)
    recommended_routes = [r for r in optimized_routes if r["recommended"]]
    
    return {
        "optimized_routes": optimized_routes,
        "recommended_routes": recommended_routes,
        "optimization_summary": {
            "total_routes_analyzed": len(optimized_routes),
            "recommended_count": len(recommended_routes),
            "average_cost": round(avg_cost, 2),
            "average_risk_score": round(avg_risk, 3),
            "best_route_id": optimized_routes[0]["id"] if optimized_routes else None,
            "optimization_weights": weights
        },
        "selection_criteria": {
            "primary_factor": "composite_score",
            "cost_weight": weights["cost"],
            "risk_weight": weights["risk"],
            "time_weight": weights["time"],
            "reliability_weight": weights["reliability"]
        }
    }


@tool
def generate_route_waypoints(origin_location: str, destination_location: str, transport_mode: str) -> Dict[str, Any]:
    """Generate intermediate waypoints for a route based on origin, destination, and transport mode.
    
    Args:
        origin_location: JSON string of origin location data
        destination_location: JSON string of destination location data
        transport_mode: Type of transport ('air', 'sea', 'land')
    
    Returns:
        Route with waypoints and estimated times
    """
    try:
        origin = json.loads(origin_location) if isinstance(origin_location, str) else origin_location
        destination = json.loads(destination_location) if isinstance(destination_location, str) else destination_location
    except (json.JSONDecodeError, TypeError):
        return {"error": "Invalid location data format"}
    
    # Mock intermediate locations based on transport mode
    waypoints = [{"location": origin, "order": 1, "estimated_arrival": None, "waypoint_type": "origin"}]
    
    # Add intermediate waypoints based on transport mode and distance
    origin_lat, origin_lng = origin.get("lat", 0), origin.get("lng", 0)
    dest_lat, dest_lng = destination.get("lat", 0), destination.get("lng", 0)
    
    # Calculate if we need intermediate stops
    distance_calc = calculate_route_distance.invoke({
        "origin_lat": origin_lat,
        "origin_lng": origin_lng, 
        "dest_lat": dest_lat,
        "dest_lng": dest_lng
    })
    distance = distance_calc["distance_km"]
    
    if distance > 2000:  # Long haul routes need intermediate stops
        if transport_mode == "sea":
            # Add major port hubs
            intermediate_ports = [
                {"id": "HUB_PORT", "name": "Dubai Port Hub", "lat": 25.2769, "lng": 55.3264, "type": "port"},
                {"id": "SUEZ", "name": "Suez Canal Transit", "lat": 30.0444, "lng": 31.2357, "type": "port"}
            ]
            for i, port in enumerate(intermediate_ports[:1]):  # Add one intermediate port
                waypoints.append({
                    "location": port,
                    "order": i + 2,
                    "estimated_arrival": f"Day {2 + i}",
                    "waypoint_type": "intermediate_port"
                })
        
        elif transport_mode == "air":
            # Add major airport hubs
            intermediate_airports = [
                {"id": "HUB_AIR", "name": "Dubai International Hub", "lat": 25.2532, "lng": 55.3657, "type": "airport"},
                {"id": "EUROPE_HUB", "name": "Frankfurt Hub", "lat": 50.0379, "lng": 8.5622, "type": "airport"}
            ]
            for i, airport in enumerate(intermediate_airports[:1]):
                waypoints.append({
                    "location": airport,
                    "order": i + 2,
                    "estimated_arrival": f"Day {1}",
                    "waypoint_type": "intermediate_hub"
                })
    
    # Add destination
    final_order = len(waypoints) + 1
    waypoints.append({
        "location": destination,
        "order": final_order,
        "estimated_arrival": f"Day {3 if transport_mode == 'sea' else 2 if transport_mode == 'air' else 4}",
        "waypoint_type": "destination"
    })
    
    # Calculate estimated duration
    duration_factors = {"air": 0.1, "sea": 1.0, "land": 0.5, "rail": 0.3}
    factor = duration_factors.get(transport_mode, 0.5)
    estimated_days = max(1, int(distance * factor / 500))
    
    return {
        "route_waypoints": waypoints,
        "total_waypoints": len(waypoints),
        "estimated_duration_days": estimated_days,
        "transport_mode": transport_mode,
        "total_distance_km": distance,
        "route_type": "long_haul" if distance > 2000 else "regional",
        "intermediate_stops": len(waypoints) - 2,  # Excluding origin and destination
        "route_summary": {
            "origin": origin.get("name", "Unknown"),
            "destination": destination.get("name", "Unknown"),
            "mode": transport_mode,
            "stops": len(waypoints)
        }
    }