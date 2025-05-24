# This is the main application file.
# It will use the weather module to fetch and display weather data.
# It attempts IP-based geolocation as a fallback if component-based geolocation fails.

import streamlit as st
import requests # For IP-based geolocation
from streamlit_geolocation import streamlit_geolocation
import geocoder
from weather import get_weather_data

# --- Enhanced Geolocation Function ---
def get_enhanced_location():
    '''Attempts to get location using browser, then geocoder, then ip-api.'''
    location_data = None
    source = None

    # 1. Try Streamlit Geolocation (Browser API)
    try:
        s_geo_data = streamlit_geolocation() # Default component key
        if s_geo_data and "latitude" in s_geo_data and "longitude" in s_geo_data:
            return {
                "latitude": s_geo_data["latitude"],
                "longitude": s_geo_data["longitude"],
                "city": "N/A (Browser Geolocation)", # Browser geo usually doesn't provide city
                "source": "browser"
            }
    except Exception as e: # Catch any error from streamlit_geolocation
        st.warning("Browser geolocation failed or permission denied. Trying IP-based lookup...")


    # 2. Try Geocoder (ip('me'))
    try:
        g = geocoder.ip('me')
        if g.ok and g.latlng:
            return {
                "latitude": g.latlng[0],
                "longitude": g.latlng[1],
                "city": g.city or "N/A (Geocoder)",
                "source": "geocoder_ip"
            }
        elif not g.ok:
             st.warning(f"Primary IP lookup (Geocoder) failed. Reason: {g.status_code if hasattr(g, 'status_code') else 'Unknown'}. Trying alternative IP lookup...")
    except Exception as e:
        st.warning(f"Primary IP lookup (Geocoder) attempt failed: {e}. Trying alternative IP lookup...")

    # 3. Fallback to existing IP-based geolocation (ip-api.com)
    # This is the original get_location_from_ip function
    # We call it directly here or you can refactor it to be callable as part of this sequence
    st.info("Falling back to ip-api.com for geolocation.")
    ip_api_location = get_location_from_ip() # Assumes get_location_from_ip() is defined in this file
    if "error" not in ip_api_location and "latitude" in ip_api_location :
        return {
            "latitude": ip_api_location["latitude"],
            "longitude": ip_api_location["longitude"],
            "city": ip_api_location.get("city", "N/A (ip-api.com)"),
            "source": "ip_api_com"
        }
    else: # Error from get_location_from_ip or no lat/lon
        error_message = ip_api_location.get("error", "All geolocation attempts failed.")
        return {"error": error_message, "source": "all_failed"}

# --- IP Geolocation Function ---
def get_location_from_ip():
    """
    Fetches approximate location (latitude, longitude) based on public IP address.
    Uses ip-api.com.
    """
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        if data.get("status") == "success" and "lat" in data and "lon" in data:
            return {"latitude": data["lat"], "longitude": data["lon"], "city": data.get("city", "N/A")}
        else:
            return {"error": data.get("message", "Failed to get location from IP.")}
    except requests.exceptions.RequestException as e:
        return {"error": f"IP geolocation request failed: {e}"}
    except Exception as e: # Catch any other parsing errors, etc.
        return {"error": f"An unexpected error occurred during IP geolocation: {e}"}


def main_streamlit():
    """
    Streamlit UI for the Weather App.
    """
    st.title("Clima Weather App")

    # User-Agent Email input
    user_agent_email = st.text_input(
        "Your Email (for NOAA API User-Agent):",
        placeholder="e.g., yourname@example.com",
        help="Required by NOAA API. Used to form User-Agent: (ClimaApp, yourname@example.com)"
    )

    st.subheader("Location")

    # Initialize session state
    if 'latitude' not in st.session_state:
        st.session_state.latitude = 39.8283  # Default: Approximate center of US
    if 'longitude' not in st.session_state:
        st.session_state.longitude = -98.5795 # Default: Approximate center of US
    if 'location_message' not in st.session_state:
        st.session_state.location_message = "Using default coordinates. Try auto-detect or enter manually."
    if 'location_source' not in st.session_state:
        st.session_state.location_source = "default"

    # Auto-detect Location Button - MODIFIED
    if st.button("Auto-detect Location"): # Changed button text
        with st.spinner("Attempting to auto-detect your location..."):
            location_data = get_enhanced_location() # Call the new function

        if "error" in location_data:
            st.session_state.location_message = f"Auto-detection Error: {location_data['error']}. Please enter coordinates manually."
            st.session_state.location_source = "error_auto" # New source for error from new function
        elif location_data and "latitude" in location_data:
            st.session_state.latitude = location_data["latitude"]
            st.session_state.longitude = location_data["longitude"]
            city = location_data.get('city', 'your area')
            source_msg_map = {
                "browser": "via browser API",
                "geocoder_ip": "approximated via IP (geocoder)",
                "ip_api_com": "approximated via IP (ip-api.com)"
            }
            source_friendly_name = source_msg_map.get(location_data.get("source"), "automatically")

            st.session_state.location_message = f"Location found {source_friendly_name} as {city} ({st.session_state.latitude:.4f}, {st.session_state.longitude:.4f}). For higher accuracy, please enter manually if needed."
            st.session_state.location_source = location_data.get("source", "auto_success") # Use the source from location_data
        else: # Should not happen if get_enhanced_location is structured correctly with an error key
            st.session_state.location_message = "Auto-detection returned no usable data. Please enter coordinates manually."
            st.session_state.location_source = "error_auto_nodata"
        
        st.experimental_rerun()


    # Display location message based on session state
    if st.session_state.location_message:
        source = st.session_state.location_source
        message = st.session_state.location_message
        
        if source in ["browser", "geocoder_ip", "ip_api_com", "auto_success", "ip_auto"]: # ip_auto kept for backward compatibility if needed
            st.success(message)
        elif source in ["error", "error_auto", "error_auto_nodata", "all_failed"]:
            st.warning(message)
        elif source == "manual_update":
             st.info(message)
        elif source == "default": # Initial default message
            st.info(message)
        else: # Catch-all for any other message types, can be styled as info or warning
            st.info(message)


    # Manual Coordinate Input
    st.write("Or enter coordinates manually:")
    col1, col2 = st.columns(2)
    with col1:
        latitude_input = st.number_input(
            "Latitude:",
            min_value=-90.0, max_value=90.0,
            value=st.session_state.latitude,
            format="%.4f",
            help="Enter latitude (-90 to 90). Can be updated by 'Auto-detect Location'.",
            key="lat_input_manual"
        )
    with col2:
        longitude_input = st.number_input(
            "Longitude:",
            min_value=-180.0, max_value=180.0,
            value=st.session_state.longitude,
            format="%.4f",
            help="Enter longitude (-180 to 180). Can be updated by 'Auto-detect Location'.",
            key="lon_input_manual"
        )
    
    # Update session state and message if manual input changes
    if latitude_input != st.session_state.latitude or longitude_input != st.session_state.longitude:
        st.session_state.latitude = latitude_input
        st.session_state.longitude = longitude_input
        st.session_state.location_message = "Manual coordinate input updated."
        st.session_state.location_source = "manual_update"
        # No rerun here to avoid loop, message will update on next natural rerun or "Get Weather"
        # However, for instant feedback on manual change, a rerun could be placed here.
        # For now, let's keep it this way to avoid too many reruns. The values are updated.

    if st.button("Get Weather"):
        if not user_agent_email or "@" not in user_agent_email:
            st.error("Please enter a valid email address for the User-Agent.")
        elif st.session_state.latitude is None or st.session_state.longitude is None:
            st.error("Latitude or Longitude is missing.")
        else:
            final_latitude = st.session_state.latitude
            final_longitude = st.session_state.longitude

            st.info(f"Fetching weather for coordinates: ({final_latitude:.4f}, {final_longitude:.4f})")
            with st.spinner("Fetching weather data from NOAA API..."):
                weather_data = get_weather_data(final_latitude, final_longitude, user_agent_email)

            if "error" in weather_data:
                st.error(f"Error: {weather_data['error']}")
            else:
                noaa_city = weather_data.get('city', 'N/A')
                noaa_state = weather_data.get('state', 'N/A')

                location_display_name = "Specified Coordinates"
                if noaa_city != 'N/A' or noaa_state != 'N/A':
                    location_display_name = f"{noaa_city}, {noaa_state}"

                st.success(f"Weather for: {location_display_name} ({final_latitude:.4f}, {final_longitude:.4f})")
                st.metric(label="Temperature", value=f"{weather_data.get('temperature', 'N/A')}°{weather_data.get('unit', '')}")
                st.write(f"**Condition:** {weather_data.get('description', 'N/A').capitalize()}")
                st.metric(label="Humidity", value=f"{weather_data.get('humidity', 'N/A')}%")

if __name__ == "__main__":
    main_streamlit()
