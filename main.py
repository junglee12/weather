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
        s_geo_data = streamlit_geolocation(key="streamlit_geolocation_component") # Added a unique key
        if s_geo_data and s_geo_data.get("latitude") is not None and s_geo_data.get("longitude") is not None:
            try:
                lat = float(s_geo_data["latitude"])
                lon = float(s_geo_data["longitude"])
                return {
                    "latitude": lat,
                    "longitude": lon,
                    "city": "N/A (Browser Geolocation)",
                    "source": "browser"
                }
            except (ValueError, TypeError):
                st.warning("Browser geolocation returned non-convertible lat/lon. Trying next method.")
        # If s_geo_data is None or lat/lon is None or conversion failed, it implicitly falls through
    except Exception as e:
        st.warning(f"Browser geolocation attempt failed: {e}. Trying next method.")


    # 2. Try Geocoder (ip('me'))
    try:
        g = geocoder.ip('me')
        if g.ok and g.latlng and len(g.latlng) == 2 and g.latlng[0] is not None and g.latlng[1] is not None:
            try:
                lat = float(g.latlng[0])
                lon = float(g.latlng[1])
                return {
                    "latitude": lat,
                    "longitude": lon,
                    "city": g.city or "N/A (Geocoder)",
                    "source": "geocoder_ip"
                }
            except (ValueError, TypeError):
                st.warning("Geocoder (ip 'me') returned non-convertible lat/lon. Trying next method.")
        elif not g.ok:
            st.warning(f"Primary IP lookup (Geocoder) failed. Status: {g.status}. Trying alternative IP lookup...")
        # If g.latlng is invalid or conversion failed, it implicitly falls through
    except Exception as e:
        st.warning(f"Primary IP lookup (Geocoder) attempt failed with exception: {e}. Trying next method.")

    # 3. Fallback to existing IP-based geolocation (ip-api.com)
    st.info("Attempting fallback IP geolocation (ip-api.com)...") # Updated message
    ip_api_location = get_location_from_ip() 
    
    # get_location_from_ip already guarantees float lat/lon if "error" is not present
    if "error" not in ip_api_location:
        # The city is already set correctly in get_location_from_ip
        # Ensure source is set for this path if successful
        ip_api_location["source"] = "ip_api_com" 
        return ip_api_location
    else:
        # Consolidate error reporting for the final fallback
        st.error(f"Final fallback IP geolocation (ip-api.com) also failed: {ip_api_location.get('error', 'Unknown reason')}")
        error_message = ip_api_location.get("error", "All geolocation attempts failed.") # Use the error from the last attempt
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
        if data.get("status") == "success":
            lat = data.get("lat")
            lon = data.get("lon")
            if lat is not None and lon is not None:
                try:
                    return {
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "city": data.get("city", "N/A (ip-api.com)") # Added source for clarity
                    }
                except (ValueError, TypeError):
                    return {"error": "Invalid location data format from IP API.", "source": "ip_api_format_error"}
            else:
                return {"error": "Incomplete location data from IP API.", "source": "ip_api_incomplete_data"}
        else:
            return {"error": data.get("message", "Failed to get location from IP API."), "source": "ip_api_failed_status"}
    except requests.exceptions.RequestException as e:
        return {"error": f"IP geolocation request failed: {e}", "source": "ip_api_request_error"}
    except Exception as e: # Catch any other parsing errors, etc.
        return {"error": f"An unexpected error occurred during IP geolocation: {e}", "source": "ip_api_unexpected_error"}


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
            
            # Safeguard before f-string formatting
            if st.session_state.latitude is not None and st.session_state.longitude is not None:
                city = location_data.get('city', 'your area') # Fallback for city
                source_msg_map = {
                    "browser": "via browser API",
                    "geocoder_ip": "approximated via IP (geocoder)",
                    "ip_api_com": "approximated via IP (ip-api.com)"
                }
                source_friendly_name = source_msg_map.get(location_data.get("source"), "automatically") # Fallback for source

                st.session_state.location_message = f"Location found {source_friendly_name} as {city} ({st.session_state.latitude:.4f}, {st.session_state.longitude:.4f}). For higher accuracy, please enter manually if needed."
                st.session_state.location_source = location_data.get("source", "auto_success")
            else:
                st.session_state.location_message = "Auto-detection returned incomplete location data. Please check values or try manual entry."
                st.session_state.location_source = "error_auto_incomplete" # New source state
        else: # This 'else' corresponds to 'elif location_data and "latitude" in location_data:'
              # It means location_data is None, or "latitude" key is missing.
              # get_enhanced_location should return an "error" key in such cases, handled by the "if 'error' in location_data" block.
              # This block is a fallback for unexpected structures from get_enhanced_location.
            st.session_state.location_message = "Auto-detection returned no usable data or unexpected format. Please enter coordinates manually."
            st.session_state.location_source = "error_auto_nodata" 
        
        st.rerun()


    # Display location message based on session state
    if st.session_state.location_message:
        source = st.session_state.location_source
        message = st.session_state.location_message
        
        if source in ["browser", "geocoder_ip", "ip_api_com", "auto_success", "ip_auto"]: 
            st.success(message)
        elif source in ["error", "error_auto", "error_auto_nodata", "all_failed", "error_auto_incomplete"]: # Added "error_auto_incomplete"
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
