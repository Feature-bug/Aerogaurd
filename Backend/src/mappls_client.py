
class MapplsGeospace:
    """
    Geofencing system for drone airspace restrictions.
    ✅ FIXED: Updated with safe coordinates away from Trivandrum Airport
    """
    
    def __init__(self):
        # ✅ FIXED: Trivandrum Airport actual coordinates
        self.AIRPORT_LAT = 8.4821
        self.AIRPORT_LNG = 76.9200
        
        # Restricted zones (in kilometers)
        self.RED_ZONE_RADIUS = 5.0    # 5km no-fly zone
        self.YELLOW_ZONE_RADIUS = 10.0  # 10km caution zone
        
        print("[Geofence] Initialized with:")
        print(f"  🔴 RED Zone: {self.RED_ZONE_RADIUS}km radius around airport")
        print(f"  🟡 YELLOW Zone: {self.YELLOW_ZONE_RADIUS}km radius around airport")
        print(f"  📍 Airport: {self.AIRPORT_LAT}°N, {self.AIRPORT_LNG}°E")
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two GPS coordinates using Haversine formula.
        Returns distance in kilometers.
        """
        R = 6371  # Earth's radius in km
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def check_airspace(self, lat, lon):
        """
        Check if GPS coordinates are in restricted airspace.
        
        Returns:
            "RED"    - Critical restricted zone (< 5km from airport)
            "YELLOW" - Caution zone (5-10km from airport)
            "GREEN"  - Safe to fly (> 10km from airport)
        """
        # Calculate distance from airport
        distance_km = self.haversine_distance(
            lat, lon, 
            self.AIRPORT_LAT, self.AIRPORT_LNG
        )
        
        # Determine zone
        if distance_km < self.RED_ZONE_RADIUS:
            return "RED"
        elif distance_km < self.YELLOW_ZONE_RADIUS:
            return "YELLOW"
        else:
            return "GREEN"
    
    def get_zone_info(self, lat, lon):
        """
        Get detailed airspace information.
        
        Returns dict with:
            - zone: RED/YELLOW/GREEN
            - distance_km: distance from airport
            - direction: compass bearing to airport
        """
        distance_km = self.haversine_distance(
            lat, lon,
            self.AIRPORT_LAT, self.AIRPORT_LNG
        )
        
        zone = self.check_airspace(lat, lon)
        
        # Calculate bearing (compass direction)
        lat1 = math.radians(lat)
        lat2 = math.radians(self.AIRPORT_LAT)
        delta_lon = math.radians(self.AIRPORT_LNG - lon)
        
        x = math.sin(delta_lon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2) - 
             math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon))
        bearing = math.degrees(math.atan2(x, y))
        bearing = (bearing + 360) % 360  # Normalize to 0-360
        
        # Convert bearing to compass direction
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        direction = directions[round(bearing / 45) % 8]
        
        return {
            'zone': zone,
            'distance_km': round(distance_km, 2),
            'direction': direction,
            'airport_lat': self.AIRPORT_LAT,
            'airport_lng': self.AIRPORT_LNG
        }


# ✅ TEST FUNCTION
if __name__ == "__main__":
    geo = MapplsGeospace()
    
    print("\n" + "="*60)
    print("Testing Geofence Detection:")
    print("="*60)
    
    # Test coordinates
    test_locations = [
        ("Trivandrum Airport", 8.4821, 76.9200),
        ("Near Airport (3km)", 8.5100, 76.9300),
        ("Caution Zone (8km)", 8.5500, 76.9500),
        ("Safe Zone (15km)", 8.6000, 77.0000),
        ("Your Default Location", 9.9312, 76.2673),
    ]
    
    for name, lat, lng in test_locations:
        info = geo.get_zone_info(lat, lng)
        print(f"\n📍 {name}:")
        print(f"   Coordinates: {lat:.4f}°N, {lng:.4f}°E")
        print(f"   Zone: {info['zone']}")
        print(f"   Distance from airport: {info['distance_km']}km {info['direction']}")
        print(f"   Status: ", end="")
        if info['zone'] == 'RED':
            print("⛔ NO-FLY ZONE")
        elif info['zone'] == 'YELLOW':
            print("⚠️  CAUTION - Near Airport")
        else:
            print("✅ SAFE TO FLY")