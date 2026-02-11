import streamlit.components.v1 as components
import streamlit as st
import base64
import os
import tempfile

# Force a clean path for the component build
def camera_component(duration_seconds=15, key=None):
    """
    A stable, native JS camera recorder for Streamlit.
    Points to a static build folder for maximum reliability.
    """
    
    if key is None:
        key = "wellio_final_camera_v7"

    # Resolve component directory
    # Since this is now in camera_component/__init__.py,
    # parent_dir is the 'camera_component' folder itself.
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend")
    
    # Declare the component once
    camera_func = components.declare_component("wellio_camera", path=build_dir)
    
    # Render the component
    return camera_func(duration_seconds=duration_seconds, key=key)

def save_camera_video(base64_data):
    """Saves the base64 video data to a temporary .webm file."""
    if not base64_data or not isinstance(base64_data, str) or "base64," not in base64_data:
        return None
        
    try:
        data_content = base64_data.split("base64,")[1]
        video_bytes = base64.b64decode(data_content)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(video_bytes)
            return tmp.name
    except Exception as e:
        st.error(f"Save Error: {e}")
        return None
    return None
