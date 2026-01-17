import math
import json
import os

class MapplsGeospace:
<<<<<<< HEAD
    def __init__(self, config_path='config.json'):
=======
    def __init__(self, config_path=None):
        # Auto-detect config.json location
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(current_dir, 'config.json'),
                os.path.join(current_dir, '..', 'config.json'),
                os.path.join(current_dir, '..', '..', 'config.json'),
                os.path.join(current_dir, 'Backend', 'config.json'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            
            if config_path is None:
                raise FileNotFoundError(
                    f"config.json not found! Searched in:\n" + 
                    "\n".join(f"  - {os.path.abspath(p)}" for p in possible_paths)
                )
        
        print(f"📍 MapplsGeospace loading config from: {os.path.abspath(config_path)}")
        
>>>>>>> b0a949453364ea05fbbc7bcda4bb954105abed67
        with open(config_path) as f:
            self.config = json.load(f)
        
        # Load simulated zones
        self.red_zone = self.config['simulation_settings']['airport_red_zone']
        self.yellow_zone = self.config['simulation_settings']['caution_yellow_zone']

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculates distance in km between two GPS points."""
        R = 6371  # Earth radius in km
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (math.sin(d_lat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def check_airspace(self, current_lat, current_lng):
        """Check if coordinates are in restricted airspace."""
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