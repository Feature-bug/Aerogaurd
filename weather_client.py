
import requests
import time

class OpenWeatherClient:
    def __init__(self, api_key):
        self.api_key = api_key
        # Using 2.5 for broader compatibility, can be switched to 3.0 if key supports it
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.cache = None
        self.last_fetch = 0
        self.cache_duration = 300 # 5 minutes

    def get_weather(self, lat, lon):
        current_time = time.time()
        if self.cache and (current_time - self.last_fetch < self.cache_duration):
            return self.cache

        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.cache = {
                    'temp': data['main'].get('temp'),
                    'humidity': data['main'].get('humidity'),
                    'wind_speed': data['wind'].get('speed'),      # m/s
                    'visibility': data.get('visibility', 10000),   # meters
                    'weather_main': data['weather'][0]['main'],    # e.g., "Rain"
                    'weather_desc': data['weather'][0]['description']
                }
                self.last_fetch = current_time
                return self.cache
            else:
                return None
        except Exception as e:
            print(f"[Weather] Request failed: {e}")
            return None
