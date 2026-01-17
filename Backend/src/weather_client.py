import requests

class OpenWeatherClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, lat, lon):
        """
        Fetch current weather at (lat, lon) using FREE API
        Returns dict with: temp, humidity, wind_speed, visibility, weather_main
        Returns None on error
        """
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric'  # Celsius, m/s
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'temp': data['main'].get('temp'),
                    'humidity': data['main'].get('humidity'),
                    'wind_speed': data['wind'].get('speed'),      # m/s
                    'visibility': data.get('visibility', 10000),   # meters
                    'weather_main': data['weather'][0]['main']     # e.g., "Rain", "Clear"
                }
            else:
                print(f"[Weather] API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"[Weather] Request failed: {e}")
            return None