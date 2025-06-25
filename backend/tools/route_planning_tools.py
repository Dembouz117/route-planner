import math
from typing import List, Dict, Any

class DistanceCalculatorTool:
    def calculate(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth's radius in kilometers
        
        return c * r

class CostEstimatorTool:
    def __init__(self):
        self.base_costs = {
            "air": 2.5,    # per km per unit
            "sea": 0.5,    # per km per unit  
            "land": 1.0    # per km per unit
        }
    
    def estimate(self, distance: float, transport_mode: str, quantity: int, risk_multiplier: float = 1.0) -> float:
        """Estimate shipping costs based on distance, mode, and quantity"""
        cost_per_km = self.base_costs.get(transport_mode, 1.0)
        base_cost = distance * cost_per_km * quantity * 0.01
        return base_cost * risk_multiplier

class RouteOptimizerTool:
    def optimize(self, candidate_routes: List[Dict]) -> List[Dict]:
        """Optimize routes based on cost, risk, and constraints"""
        # Sort routes by a composite score (cost + risk factor)
        def calculate_score(route):
            cost_weight = 0.6
            risk_weight = 0.4
            
            # Normalize cost (assuming max cost is 10000)
            cost_score = min(route["total_cost"] / 10000, 1.0)
            risk_score = route["risk_score"]
            
            return (cost_score * cost_weight) + (risk_score * risk_weight)
        
        # Sort by composite score (lower is better)
        optimized = sorted(candidate_routes, key=calculate_score)
        
        # Add optimization metadata
        for i, route in enumerate(optimized):
            route["optimization_rank"] = i + 1
            route["composite_score"] = calculate_score(route)
            route["recommended"] = i < 3  # Top 3 routes recommended
        
        return optimized