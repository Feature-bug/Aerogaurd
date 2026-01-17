# weather_client.py
import requests
import json
import os

class OpenWeatherClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"

    def get_weather(self, lat, lon):
        """
        Fetch current weather at (lat, lon)
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
                current = data['current']
                return {
                    'temp': current.get('temp'),
                    'humidity': current.get('humidity'),
                    'wind_speed': current.get('wind_speed'),      # m/s
                    'visibility': current.get('visibility', 10000), # meters (default 10km if missing)
                    'weather_main': current['weather'][0]['main']  # e.g., "Rain", "Clear", "Fog"
                }
            else:
                print(f"[Weather] API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"[Weather] Request failed: {e}")
            return None