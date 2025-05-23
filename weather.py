# This file will contain the logic to fetch weather data using the NOAA API.
import json
import requests

def get_weather_data(latitude: float, longitude: float, user_agent_email: str = "clima@example.com") -> dict:
    """
    Fetches weather data from the NOAA API.

    Args:
        latitude: The latitude of the location.
        longitude: The longitude of the location.
        user_agent_email: Email address to use in the User-Agent header.

    Returns:
        A dictionary containing relevant weather information,
        or a dictionary with an "error" key if an error occurs.
    """
    if not user_agent_email: # Ensure there's a default if an empty string is passed
        user_agent_email = "clima@example.com"
        
    user_agent = f"(ClimaApp, {user_agent_email})"
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/geo+json" # Recommended by NOAA API for points endpoint
    }

    # Step 1: Get Grid Information (including the hourly forecast URL)
    # NOAA API is sensitive to trailing zeros for coordinates.
    # Let's format them to have one decimal place or no decimal if it's .0
    lat_str = f"{latitude:.1f}".rstrip('0').rstrip('.')
    lon_str = f"{longitude:.1f}".rstrip('0').rstrip('.')
    points_url = f"https://api.weather.gov/points/{lat_str},{lon_str}"

    try:
        points_response = requests.get(points_url, headers=headers, timeout=10)
        points_response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        points_data = points_response.json()

        forecast_hourly_url = points_data.get("properties", {}).get("forecastHourly")
        if not forecast_hourly_url:
            # Check if it's a 301 redirect due to coordinate formatting
            if points_response.status_code == 301 and points_response.headers.get("Location"):
                 return {"error": f"Coordinate redirect: API suggests using {points_response.headers['Location']}. Original: {points_url}"}
            return {"error": "Could not find 'forecastHourly' URL in NOAA points response."}

    except requests.exceptions.Timeout:
        return {"error": f"Timeout when contacting NOAA points API at {points_url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error accessing NOAA points API ({points_url}): {e}"}
    except json.JSONDecodeError:
        return {"error": f"Error decoding JSON response from NOAA points API ({points_url})."}
    except (KeyError, AttributeError) as e: # More specific for dict/attribute access
        return {"error": f"Error parsing data from NOAA points API response ({points_url}): {e}"}


    # Step 2: Get Hourly Forecast
    try:
        # Ensure the User-Agent is also sent for this request
        hourly_headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
        hourly_response = requests.get(forecast_hourly_url, headers=hourly_headers, timeout=10)
        hourly_response.raise_for_status()
        hourly_data = hourly_response.json()

        periods = hourly_data.get("properties", {}).get("periods")
        if not periods or not isinstance(periods, list) or len(periods) == 0:
            return {"error": "No forecast periods found in NOAA hourly forecast response."}

        # Take the first period
        current_forecast = periods[0]

        temperature = current_forecast.get("temperature")
        temp_unit = current_forecast.get("temperatureUnit")
        humidity_data = current_forecast.get("relativeHumidity", {})
        humidity_value = humidity_data.get("value") # This could be None if 'value' is missing
        short_forecast = current_forecast.get("shortForecast")
        
        # Basic validation for essential data
        if temperature is None or temp_unit is None or humidity_value is None or short_forecast is None:
            missing_fields = []
            if temperature is None: missing_fields.append("temperature")
            if temp_unit is None: missing_fields.append("temperatureUnit")
            if humidity_value is None: missing_fields.append("humidity")
            if short_forecast is None: missing_fields.append("shortForecast")
            return {"error": f"Missing essential weather data in NOAA forecast period: {', '.join(missing_fields)}."}

        weather_info = {
            "temperature": temperature,
            "unit": temp_unit,
            "humidity": humidity_value,
            "description": short_forecast,
            # Attempt to add city/state from points_data if available
            "city": points_data.get("properties", {}).get("relativeLocation", {}).get("properties", {}).get("city"),
            "state": points_data.get("properties", {}).get("relativeLocation", {}).get("properties", {}).get("state")
        }
        return weather_info

    except requests.exceptions.Timeout:
        return {"error": f"Timeout when contacting NOAA hourly forecast API at {forecast_hourly_url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error accessing NOAA hourly forecast API ({forecast_hourly_url}): {e}"}
    except json.JSONDecodeError:
        return {"error": f"Error decoding JSON response from NOAA hourly forecast API ({forecast_hourly_url})."}
    except (KeyError, IndexError, AttributeError) as e: # More specific for dict/list/attribute access
        return {"error": f"Error parsing data from NOAA hourly forecast response ({forecast_hourly_url}): {e}"}
    except Exception as e: # Catch-all for any other unexpected error during parsing
        return {"error": f"An unexpected error occurred while processing weather data: {e}"}
