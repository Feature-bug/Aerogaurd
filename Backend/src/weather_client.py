import random
import time
import math

class OpenWeatherClient:
    def __init__(self, api_key=None):
        """
        Weather client that works with or without API key.
        Falls back to local simulation if no API key provided.
        """
        self.api_key = api_key
        self.use_api = (api_key and 
                       api_key != "YOUR_KEY_HERE" and 
                       api_key != "" and 
                       len(api_key) > 10)
        
        # Simulated weather base conditions
        self.base_conditions = {
            'temp': 28.0,
            'humidity': 65,
            'wind_speed': 3.5,
            'visibility': 10000,
            'weather_main': 'Clear'
        }
        
        mode = "API Mode" if self.use_api else "Local Simulation"
        print(f"[Weather Client] Initialized in {mode}")

    def get_weather(self, lat, lon):
        """
        Fetch current weather at (lat, lon).
        Returns dict with: temp, humidity, wind_speed, visibility, weather_main
        """
        
        # Try real API if key is valid
        if self.use_api:
            try:
                import requests
                # FIXED: Use correct free API endpoint
                base_url = "https://api.openweathermap.org/data/2.5/weather"
                params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': self.api_key,
                    'units': 'metric'
                }
                
                response = requests.get(base_url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'temp': data['main'].get('temp'),
                        'humidity': data['main'].get('humidity'),
                        'wind_speed': data['wind'].get('speed'),
                        'visibility': data.get('visibility', 10000),
                        'weather_main': data['weather'][0]['main']
                    }
                else:
                    print(f"[Weather] API Error {response.status_code}, using simulation")
            except Exception as e:
                print(f"[Weather] API failed: {e}, using simulation")
        
        # Local simulation fallback
        return self._simulate_weather(lat, lon)
    
    def _simulate_weather(self, lat, lon):
        """Generate realistic simulated weather."""
        # Time-based temperature variation
        hour = time.localtime().tm_hour
        temp_variation = 5 * math.sin((hour - 6) * math.pi / 12)
        
        # Random noise for realism
        noise = random.uniform(-0.5, 0.5)
        
        weather_data = {
            'temp': round(self.base_conditions['temp'] + temp_variation + noise, 1),
            'humidity': max(30, min(95, self.base_conditions['humidity'] + random.randint(-3, 3))),
            'wind_speed': round(max(0, self.base_conditions['wind_speed'] + random.uniform(-0.5, 0.5)), 1),
            'visibility': self.base_conditions['visibility'],
            'weather_main': self.base_conditions['weather_main']
        }
        
        return weather_data
    
    def set_weather_condition(self, condition):
        """
        Manually set weather conditions for testing.
        Examples: 'Clear', 'Rain', 'Thunderstorm', 'Fog', 'Snow'
        """
        conditions_map = {
            'Clear': {'wind_speed': 3.5, 'visibility': 10000, 'weather_main': 'Clear'},
            'Rain': {'wind_speed': 8.0, 'visibility': 7000, 'weather_main': 'Rain'},
            'Thunderstorm': {'wind_speed': 15.0, 'visibility': 3000, 'weather_main': 'Thunderstorm'},
            'Fog': {'wind_speed': 2.0, 'visibility': 1000, 'weather_main': 'Fog'},
            'Snow': {'wind_speed': 6.0, 'visibility': 4000, 'weather_main': 'Snow'},
            'High Wind': {'wind_speed': 12.0, 'visibility': 10000, 'weather_main': 'Clear'}
        }
        
        if condition in conditions_map:
            self.base_conditions.update(conditions_map[condition])
            print(f"[Weather] Condition set to: {condition}")
            return True
        else:
            print(f"[Weather] Unknown condition: {condition}")
            return False