import streamlit.components.v1 as components
import streamlit as st
import base64
import os
import tempfile

# Standardize the component folder path
# This assumes the directory structure:
# camera_component/
#   frontend/
#     index.html
def camera_component(duration_seconds=15, key=None):
    """
    A stable, native JS camera recorder for Streamlit.
    Points to a static build folder for maximum reliability.
    """
    
    if key is None:
        key = "wellio_final_camera_v7"

    # Resolve component directory
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "camera_component", "frontend")
    
    # Fallback for local dev vs package structure
    if not os.path.exists(build_dir):
        # Check if we are inside the camera_component directory
        if os.path.basename(parent_dir) == "camera_component":
             build_dir = os.path.join(parent_dir, "frontend")
        else:
             # Look in current working directory as last resort
             build_dir = os.path.abspath("camera_component/frontend")

    # Declare the component once
    # On Streamlit Cloud, it's safer to use the relative path if possible
    # but declare_component works well with absolute paths.
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
