import math
import json

class MapplsGeospace:
    def __init__(self, config_path='config.json'):
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
        a = (math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def check_airspace(self, current_lat, current_lng):
        # Calculate distance from 'Airport'
        dist = self.haversine_distance(current_lat, current_lng, self.red_zone['lat'], self.red_zone['lng'])
        
        if dist <= self.red_zone['radius_km']:
            return "RED"
        elif dist <= self.yellow_zone['radius_km']:
            return "YELLOW"
        else:
            return "GREEN"
