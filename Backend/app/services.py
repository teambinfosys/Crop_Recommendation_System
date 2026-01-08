import requests
from datetime import datetime, timedelta

def get_coordinates(location: str):
    """
    Fetches latitude and longitude for a given location using Open-Meteo Geocoding API.
    """
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        response = requests.get(url)
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return result["latitude"], result["longitude"]
        return None, None
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
        return None, None

def get_weather_data(lat: float, lon: float, season: str):
    """
    Fetches historical weather data (aggregated) for a specific season from Open-Meteo Archive API.
    Uses the previous completed year for reliable historical data.
    """
    try:
        # Define season dates (approximate for India)
        # Using previous year to ensure data availability
        current_year = datetime.now().year
        # If we are in early 2026, previous year is 2025
        target_year = current_year - 1 
        
        season = season.lower()
        
        if season == 'kharif':
            start_date = f"{target_year}-06-01"
            end_date = f"{target_year}-09-30"
        elif season == 'rabi':
            # Rabi spans across years (Oct to Feb)
            # For "Previous Year" Rabi, we use Oct of (target_year-1) to Feb of (target_year)
            # Or simpler: Oct of target_year to Feb of target_year+1 (if target_year is in past)
            # Let's stick to the user's simpler example year logic for robustness:
            start_date = f"{target_year}-10-01"
            # End date is next year Feb
            end_date = f"{target_year + 1}-02-28"
        elif season == 'zaid': # Summer
            start_date = f"{target_year}-03-01"
            end_date = f"{target_year}-05-31"
        else:
            # Default to Zaid if unknown
            start_date = f"{target_year}-03-01"
            end_date = f"{target_year}-05-31"

        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "daily": ["temperature_2m_mean", "relative_humidity_2m_mean", "precipitation_sum"],
            "timezone": "Asia/Kolkata"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if "daily" not in data:
            raise ValueError("Weather data not found")

        daily = data["daily"]
        
        # Aggregate
        temps = [t for t in daily["temperature_2m_mean"] if t is not None]
        hums = [h for h in daily["relative_humidity_2m_mean"] if h is not None]
        rains = [r for r in daily["precipitation_sum"] if r is not None]
        
        avg_temp = round(sum(temps) / len(temps), 2) if temps else 0
        avg_hum = round(sum(hums) / len(hums), 2) if hums else 0
        total_rain = round(sum(rains), 2) if rains else 0
        
        return {
            "temperature": avg_temp,
            "humidity": avg_hum,
            "rainfall": total_rain
        }
        
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        # Return fallback/dummy data if API fails to prevent app crash
        return {
            "temperature": 25.0,
            "humidity": 60.0,
            "rainfall": 100.0
        }
