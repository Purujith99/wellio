"""
User Profile Manager
====================

Handles loading and saving user profile data to Supabase.
"""

from typing import Optional, Dict, Any
from auth import get_supabase_client

def get_user_profile(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile data from Supabase.
    
    Args:
        email: User email
        
    Returns:
        Dictionary of profile data or None if not found/error
    """
    if not email:
        return None
        
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return None
            
        response = supabase.table('user_profiles').select('*').eq('user_email', email.lower()).execute()
        
        if not response.data:
            return None
            
        return response.data[0]
        
    except Exception as e:
        print(f"Error getting user profile: {e}")
        return None


def save_user_profile(email: str, profile_data: Dict[str, Any]) -> bool:
    """
    Save or update user profile data in Supabase.
    
    Args:
        email: User email
        profile_data: Dictionary containing profile fields (age, weight, etc.)
        
    Returns:
        True if successful
    """
    if not email or not profile_data:
        return False
        
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return False
            
        # Prepare data for upsert
        data = profile_data.copy()
        data['user_email'] = email.lower()
        
        # Upsert (insert or update on conflict)
        supabase.table('user_profiles').upsert(data, on_conflict='user_email').execute()
        return True
        
    except Exception as e:
        print(f"Error saving user profile: {e}")
        return False
