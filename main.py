# This is the main application file.
# It will use the weather module to fetch and display weather data.
# It attempts IP-based geolocation as a fallback if component-based geolocation fails.

import streamlit as st
import requests # For IP-based geolocation
from weather import get_weather_data

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

    # IP-based Geolocation Button
    if st.button("Auto-detect Location (IP-based)"):
        with st.spinner("Attempting IP-based geolocation..."):
            location_data = get_location_from_ip()
        
        if "error" in location_data:
            st.session_state.location_message = f"IP Geolocation Error: {location_data['error']}. Please enter coordinates manually."
            st.session_state.location_source = "error"
        elif location_data.get("latitude") is not None:
            st.session_state.latitude = location_data["latitude"]
            st.session_state.longitude = location_data["longitude"]
            city = location_data.get('city', 'your area')
            st.session_state.location_message = f"Location approximated via IP to {city} ({st.session_state.latitude:.4f}, {st.session_state.longitude:.4f}). For higher accuracy, please enter manually."
            st.session_state.location_source = "ip_auto"
        # We need to trigger a rerun for the message and input fields to update immediately
        st.experimental_rerun()


    # Display location message based on session state (success, error, info)
    if st.session_state.location_message:
        if st.session_state.location_source == "ip_auto" or "Successfully" in st.session_state.location_message : # Treat ip_auto as a success type message
            st.success(st.session_state.location_message)
        elif st.session_state.location_source == "error" or "Error" in st.session_state.location_message:
            st.warning(st.session_state.location_message)
        elif st.session_state.location_source == "manual_update":
             st.info(st.session_state.location_message)
        elif st.session_state.location_source == "default": # Initial default message
            st.info(st.session_state.location_message)


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
