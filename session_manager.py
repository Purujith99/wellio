"""
Session Manager Module
======================

Handles secure 3-layer session persistence:
1. Browser Cookies (Auth Token)
2. Streamlit Session State (User Profile, Navigation)
3. Runtime State (rPPG/Camera Guards)
"""

import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time
from typing import Optional

# Import auth module
try:
    from auth import validate_session_token, create_session, logout_session, get_user
    HAVE_AUTH = True
except ImportError:
    HAVE_AUTH = False

class SessionManager:
    """
    Centralized manager for session persistence using URL Query Parameters.
    """
    
    def __init__(self):
        # Native Streamlit query params - no external component needed
        pass
        
    def get_session_token(self) -> Optional[str]:
        """Retrieve session token from URL query params"""
        return st.query_params.get("session_id", None)

    def set_session_token(self, token: str):
        """
        Set session token in URL query params.
        Valid for effectively "forever" (until URL is cleared or browser closed).
        """
        st.query_params["session_id"] = token

    def clear_session(self):
        """
        Clear session info from URL and memory
        """
        # 1. Clear query params
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        if "page" in st.query_params:
            del st.query_params["page"]
            
        # 2. Clear auth state in session_state
        if "logged_in" in st.session_state:
            st.session_state["logged_in"] = False
        if "user_email" in st.session_state:
            st.session_state["user_email"] = None
        if "user_name" in st.session_state:
            st.session_state["user_name"] = None
        
        # 3. Clear runtime state (rPPG guards)
        self.reset_runtime_state()
            
    def restore_session(self) -> bool:
        """
        Attempt to restore session from URL query params.
        Returns True if session was restored, False otherwise.
        """
        if not HAVE_AUTH:
            return False
            
        # Check if already logged in (memory state)
        if st.session_state.get("logged_in", False):
            return True
            
        # Check for token in URL
        token = self.get_session_token()
        
        if token:
            user = validate_session_token(token)
            if user:
                # Valid session found
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = user.email
                st.session_state["user_name"] = user.name
                st.session_state["user_language"] = user.language
                
                # Try to restore page from URL
                saved_page = st.query_params.get("page", None)
                if saved_page:
                    st.session_state["current_page"] = saved_page
                    
                # Initialize runtime state immediately
                self.init_runtime_state()
                return True
            else:
                # Invalid token - unlikely unless URL copied/expired
                self.clear_session()
                return False
        
        return False

    def init_runtime_state(self):
        """
        Initialize critical runtime variables for rPPG/Camera safety.
        """
        # Phase 4: Runtime Guards
        defaults = {
            # rPPG / Camera
            "is_recording": False,
            "analysis_started": False,
            "camera_active": False,
            
            # Vitals Cache
            "vitals": None,
            "filtered_signal": None,
            "risk_assessment": None,
            
            # UI State
            "show_signup": False,
            "current_page": "Home",
            
            # Chatbot
            "chat_messages": [],
            "chatbot_open": False
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def update_current_page(self, page_name: str):
        """
        Update the current page for persistence.
        """
        st.session_state["current_page"] = page_name

    def reset_runtime_state(self):
        """
        Reset runtime state on logout to prevent data leaks.
        """
        keys_to_clear = [
            "is_recording", "analysis_started", "camera_active",
            "vitals", "filtered_signal", "risk_assessment",
            "chat_messages", "chatbot_open",
            "viewing_history", "viewing_trends",
            "profile_completed"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                
        # Reset page to Home
        st.session_state["current_page"] = "Home"

    def set_page(self, page_name: str):
        """
        Set current page and update session flags.
        """
        self.update_current_page(page_name)
        
        # Persist page to URL
        st.query_params["page"] = page_name
        
        self.sync_page_state()

    def sync_page_state(self):
        """
        Sync session flags based on current_page.
        """
        page = st.session_state.get("current_page", "Home")
        
        # Reset all view flags
        st.session_state["viewing_history"] = False
        st.session_state["viewing_all_history"] = False
        st.session_state["viewing_trends"] = False
        
        # Set active flag
        if page == "History":
            st.session_state["viewing_history"] = True
        elif page == "AllHistory":
            st.session_state["viewing_all_history"] = True
        elif page == "Trends":
            st.session_state["viewing_trends"] = True
        # "Home" leaves all flags False

def get_session_manager():
    """
    Factory for SessionManager.
    No need for caching or complex lifecycle management with native Query Params.
    """
    return SessionManager()
