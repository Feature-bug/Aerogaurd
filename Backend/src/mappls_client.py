import math
import json
import os

class MapplsGeospace:
    def __init__(self, config_path=None):
        if config_path is None:
            # Auto-detect config.json location
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(os.path.dirname(current_dir), 'config.json')
        
        try:
            with open(config_path) as f:
                self.config = json.load(f)
            print(f"[Geofence] Config loaded from: {config_path}")
        except FileNotFoundError:
            print(f"[Geofence] Config not found, using defaults")
            self.config = {
                "simulation_settings": {
                    "airport_red_zone": {"lat": 9.9401, "lng": 76.2701, "radius_km": 2.0},
                    "caution_yellow_zone": {"lat": 9.9401, "lng": 76.2701, "radius_km": 5.0}
                }
            }
        
        # Load simulated zones
        self.red_zone = self.config['simulation_settings']['airport_red_zone']
        self.yellow_zone = self.config['simulation_settings']['caution_yellow_zone']

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculates distance in km between two GPS points."""
        R = 6371  # Earth radius in km
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(d_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def check_airspace(self, current_lat, current_lng):
        """Check which airspace zone the drone is in."""
        # Calculate distance from 'Airport'
        dist = self.haversine_distance(
            current_lat, current_lng, 
            self.red_zone['lat'], self.red_zone['lng']
        )
        
        if dist <= self.red_zone['radius_km']:
            return "RED"
        elif dist <= self.yellow_zone['radius_km']:
            return "YELLOW"
        else:
            return "GREEN"