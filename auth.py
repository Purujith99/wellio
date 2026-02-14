"""
User Authentication Module with Supabase
=========================================

Secure user authentication with bcrypt password hashing and Supabase cloud database
for the Wellio health monitoring application.

Security Features:
- bcrypt password hashing with automatic salting
- Supabase PostgreSQL cloud database
- Email validation
- Password strength validation
- Duplicate email prevention
- Secure cloud storage
"""

import bcrypt
import re
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid
from typing import Optional, Tuple, List
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class User:
    """User account data"""
    email: str
    password_hash: str
    name: str
    language: str = "en"
    created_at: str = ""
    last_login: Optional[str] = None


# ============================================================================
# SUPABASE CONFIGURATION
# ============================================================================

def get_supabase_client() -> Optional[Client]:
    """
    Get Supabase client instance.
    
    Returns:
        Supabase client or None if credentials not found
    """
    # Priority 1: Environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    
    # Priority 2: Streamlit Secret Storage (for cloud deployment)
    if not url or not key:
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                if "SUPABASE_URL" in st.secrets:
                    url = st.secrets["SUPABASE_URL"]
                if "SUPABASE_KEY" in st.secrets:
                    key = st.secrets["SUPABASE_KEY"]
                
                # Also check inside a 'supabase' section if it exists
                if not url and "supabase" in st.secrets:
                    url = st.secrets["supabase"].get("URL")
                    key = st.secrets["supabase"].get("KEY")
        except Exception:
            # streamlit might not be installed or initialized
            pass
            
    # Priority 3: Hardcoded fallbacks REMOVED for security
    # Keys must be provided via environment variables, .env file, or secrets.toml

    
    
    # Priority 3: Manual .env file reading (Last resort fallback)
    if not url or not key:
        env_path = Path(".env")
        try:
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        if line.startswith("SUPABASE_URL="):
                            url = line.split("=", 1)[1].strip()
                        elif line.startswith("SUPABASE_KEY="):
                            key = line.split("=", 1)[1].strip()
        except Exception:
            pass

    if not url or not key:
        from dotenv import find_dotenv
        env_file = find_dotenv()
        details = f"URL={'found' if url else 'MISSING'}, KEY={'found' if key else 'MISSING'}. "
        details += f"CWD={os.getcwd()}, .env={env_file or 'NOT FOUND'}. "
        if env_file and os.path.exists(env_file):
             details += f"File size={os.path.getsize(env_file)} bytes."
             
        error_msg = (
            f"Supabase credentials not found. {details}\n\n"
            "IF YOU ARE ON STREAMLIT CLOUD: You must add 'SUPABASE_URL' and 'SUPABASE_KEY' "
            "to your App Settings > Secrets.\n\n"
            "IF YOU ARE LOCAL: Ensure you have a .env file with these keys."
        )
        return None, error_msg
    
    try:
        return create_client(url, key), None
    except Exception as e:
        return None, f"Error creating Supabase client: {str(e)}"


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt with automatic salt generation.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against stored hash.
    
    Args:
        password: Plain text password to verify
        password_hash: Stored bcrypt hash
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


# ============================================================================
# VALIDATION
# ============================================================================

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Please enter a valid email address"
    
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    
    Args:
        password: Password to validate
        
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, ""


def get_password_strength(password: str) -> str:
    """
    Get password strength indicator.
    
    Args:
        password: Password to evaluate
        
    Returns:
        "Weak", "Medium", or "Strong"
    """
    score = 0
    
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    
    if score <= 2:
        return "Weak"
    elif score <= 4:
        return "Medium"
    else:
        return "Strong"


# ============================================================================
# USER MANAGEMENT (SUPABASE)
# ============================================================================

def user_exists(email: str) -> bool:
    """
    Check if user with email exists in Supabase.
    
    Args:
        email: Email address to check
        
    Returns:
        True if user exists, False otherwise
    """
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return False
        
        response = supabase.table('users').select('email').eq('email', email.lower()).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False


def get_user(email: str) -> Optional[User]:
    """
    Get user from Supabase by email.
    
    Args:
        email: Email address
        
    Returns:
        User object if found, None otherwise
    """
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.table('users').select('*').eq('email', email.lower()).execute()
        
        if not response.data:
            return None
        
        user_data = response.data[0]
        return User(
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            name=user_data['name'],
            language=user_data.get('language', 'en'),
            created_at=user_data['created_at'],
            last_login=user_data.get('last_login')
        )
    except Exception as e:
        print(f"Error getting user: {e}")
        return None


def create_user(email: str, password: str, name: str, language: str = "en") -> Tuple[bool, str]:
    """
    Create new user account in Supabase.
    
    Args:
        email: User email
        password: Plain text password
        name: User full name
        language: Preferred language (en, hi, te)
        
    Returns:
        (success: bool, message: str)
    """
    # Validate email
    valid_email, email_msg = validate_email(email)
    if not valid_email:
        return False, email_msg
    
    # Validate password
    valid_pass, pass_msg = validate_password(password)
    if not valid_pass:
        return False, pass_msg
    
    # Validate name
    if not name or len(name.strip()) < 2:
        return False, "Please enter your full name"
    
    try:
        supabase, error_msg = get_supabase_client()
        if not supabase:
            return False, f"Database connection error: {error_msg or 'Unknown error'}"
        
        # Check if user already exists
        if user_exists(email):
            return False, "An account with this email already exists. Please login."
        
        # Hash password
        password_hash = hash_password(password)
        
        # Insert user into Supabase
        # Note: language field temporarily removed until database schema is updated
        data = {
            'email': email.lower(),
            'password_hash': password_hash,
            'name': name.strip(),
            'created_at': datetime.now().isoformat()
        }
        
        supabase.table('users').insert(data).execute()
        
        return True, "Account created successfully!"
    
    except Exception as e:
        print(f"Error creating user: {e}")
        return False, f"Error creating account: {str(e)}"


def authenticate_user(email: str, password: str) -> Tuple[bool, Optional[User], str]:
    """
    Authenticate user credentials against Supabase.
    
    Args:
        email: User email
        password: Plain text password
        
    Returns:
        (success: bool, user: Optional[User], message: str)
    """
    # Validate inputs
    if not email or not password:
        return False, None, "Please enter both email and password"
    
    try:
        supabase, error_msg = get_supabase_client()
        if not supabase:
            return False, None, f"Database connection error: {error_msg or 'Unknown error'}"
        
        # Get user from Supabase
        response = supabase.table('users').select('*').eq('email', email.lower()).execute()
        
        if not response.data:
            return False, None, "Invalid email or password"
        
        user_data = response.data[0]
        
        # Verify password
        if not verify_password(password, user_data['password_hash']):
            return False, None, "Invalid email or password"
        
        # Update last_login timestamp
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('email', email.lower()).execute()
        
        # Create User object
        user = User(
            email=user_data['email'],
            password_hash=user_data['password_hash'],
            name=user_data['name'],
            language=user_data.get('language', 'en'),
            created_at=user_data['created_at'],
            last_login=datetime.now().isoformat()
        )
        
        return True, user, "Login successful!"
    
    except Exception as e:
        print(f"Authentication error: {e}")
        return False, None, f"Authentication error: {str(e)}"


def update_user_login(email: str) -> bool:
    """
    Update user's last login timestamp in Supabase.
    
    Args:
        email: User email
        
    Returns:
        True if successful
    """
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return False
        
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('email', email.lower()).execute()
        
        return True
    except Exception as e:
        print(f"Error updating login: {e}")
        return False


def update_user_language(email: str, language: str) -> bool:
    """
    Update user's language preference in Supabase.
    
    Args:
        email: User email
        language: Language code ('en', 'hi', 'te')
        
    Returns:
        True if successful
    """
    # Validate language
    if language not in ['en', 'hi', 'te']:
        return False
    
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return False
        
        supabase.table('users').update({
            'language': language
        }).eq('email', email.lower()).execute()
        
        return True
    except Exception as e:
        print(f"Error updating language: {e}")
        return False


def update_user_name(email: str, new_name: str) -> Tuple[bool, str]:
    """
    Update user's name in Supabase.
    
    Args:
        email: User email
        new_name: New name to set
        
    Returns:
        (success: bool, message: str)
    """
    if not new_name or len(new_name.strip()) < 2:
        return False, "Name must be at least 2 characters long"
        
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return False, "Database connection error"
        
        supabase.table('users').update({
            'name': new_name.strip()
        }).eq('email', email.lower()).execute()
        
        return True, "Name updated successfully"
    except Exception as e:
        print(f"Error updating name: {e}")
        return False, f"Error updating name: {str(e)}"

# ============================================================================
# GOOGLE OAUTH
# ============================================================================

def get_google_auth_url(redirect_to: str = None, supabase_client: Optional[Client] = None) -> Optional[str]:
    """
    Get Google OAuth URL for sign-in.
    
    Args:
        redirect_to: URL to redirect after successful login. Defaults to APP_URL env var or localhost:8501.
        supabase_client: Optional client to preserve PKCE session
        
    Returns:
        OAuth URL string or None if error
    """
    if redirect_to is None:
        redirect_to = os.environ.get("APP_URL", "http://localhost:8501")

    try:
        if supabase_client:
             supabase = supabase_client
        else:
             supabase, _ = get_supabase_client()
             
        if not supabase:
            return None
        
        # Use provider='google'
        data = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_to
            }
        })
        
        return data.url
    except Exception as e:
        print(f"Error getting Google auth URL: {e}")
        return None


def exchange_code_for_session(auth_code: str, supabase_client: Optional[Client] = None) -> Tuple[bool, Optional[User], str]:
    """
    Exchange authorization code for session.
    
    Args:
        auth_code: Authorization code from URL query param
        supabase_client: Optional client to preserve PKCE session
        
    Returns:
        (success: bool, user: Optional[User], message: str)
    """
    try:
        if supabase_client:
             supabase = supabase_client
        else:
             supabase, error_msg = get_supabase_client()
             
        if not supabase:
            return False, None, f"Database connection error: {error_msg or 'Unknown error'}"
            
        # Exchange code for session
        response = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
        
        if not response.user:
            return False, None, "Failed to retrieve user data"
            
        user_data = response.user
        
        # Check if user exists in our 'users' table or insert them if new
        # Note: Supabase Auth manages users separately from our public.users table 
        # unless we use triggers. To keep it simple, we'll upsert into our users table.
        
        # Extract user info
        email = user_data.email
        name = user_data.user_metadata.get('full_name', email.split('@')[0])
        
        # Upsert into public.users table to ensure we have a record
        # We might not have a password hash for OAuth users, so we can use a placeholder or handle it
        # For now, we'll try to find existing or create new
        
        if not user_exists(email):
             # Create a record in our custom users table
             # Use a dummy hash for oauth users or modify schema to allow null
             # We use a randomized password so no one can login with password
             dummy_hash = hash_password("OAUTH_USER_" + os.urandom(8).hex())
             
             data = {
                'email': email.lower(),
                'password_hash': dummy_hash,
                'name': name,
                'created_at': datetime.now().isoformat(),
                # 'language': 'en', # REMOVED: Column does not exist in schema
                'last_login': datetime.now().isoformat()
            }
             supabase.table('users').insert(data).execute()
        else:
            # Update last login
            supabase.table('users').update({
                'last_login': datetime.now().isoformat()
            }).eq('email', email.lower()).execute()
            
        # Get full user data from our table to return consistent User object
        # If get_user fails (e.g. slight delay), construct one from OAuth data
        db_user = get_user(email)
        if db_user:
            return True, db_user, "Login successful!"
            
        return True, User(
            email=email,
            password_hash="",
            name=name,
            language="en",
            created_at=datetime.now().isoformat(),
            last_login=datetime.now().isoformat()
        ), "Login successful!"
        
    except Exception as e:
        print(f"Error exchanging code: {e}")
        return False, None, f"Authentication error: {str(e)}"



# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_count() -> int:
    """Get total number of registered users from Supabase"""
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return 0
        
        response = supabase.table('users').select('email', count='exact').execute()
        return response.count if hasattr(response, 'count') else len(response.data)
    except Exception as e:
        print(f"Error getting user count: {e}")
        return 0


def delete_user(email: str) -> Tuple[bool, str]:
    """
    Delete user account from Supabase (admin function).
    
    Args:
        email: User email to delete
        
    Returns:
        (success: bool, message: str)
    """
    try:
        supabase, error_msg = get_supabase_client()
        if not supabase:
            return False, f"Database connection error: {error_msg or 'Unknown error'}"
        
        supabase.table('users').delete().eq('email', email.lower()).execute()
        return True, "User deleted successfully"
    except Exception as e:
        print(f"Error deleting user: {e}")
# ============================================================================
# SESSION MANAGEMENT (PERSISTENCE)
# ============================================================================

def create_session(email: str) -> Tuple[Optional[str], str]:
    """
    Create a new login session and return the token.
    
    Args:
        email: User email
        
    Returns:
        (token, error_message)
    """
    try:
        supabase, error = get_supabase_client()
        if not supabase:
            return None, f"DB Error: {error}"
            
        # Generate token
        token = str(uuid.uuid4())
        
        # Set expiry (30 days)
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        data = {
            'user_email': email.lower(),
            'token': token,
            'expires_at': expires_at
        }
        
        supabase.table('sessions').insert(data).execute()
        return token, ""
    except Exception as e:
        print(f"Error creating session: {e}")
        return None, str(e)


def validate_session_token(token: str) -> Optional[User]:
    """
    Validate session token and return associated User.
    
    Args:
        token: Session token
        
    Returns:
        User object if valid, None otherwise
    """
    if not token:
        return None
        
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return None
            
        # Check if token exists and is not expired
        now = datetime.utcnow().isoformat()
        response = supabase.table('sessions').select('user_email').eq('token', token).gt('expires_at', now).execute()
        
        if not response.data:
            return None
            
        email = response.data[0]['user_email']
        return get_user(email)
        
    except Exception as e:
        print(f"Error validating session: {e}")
        return None


def logout_session(token: str) -> bool:
    """
    Delete session token (logout).
    
    Args:
        token: Session token
        
    Returns:
        True if successful
    """
    if not token:
        return False
        
    try:
        supabase, _ = get_supabase_client()
        if not supabase:
            return False
            
        supabase.table('sessions').delete().eq('token', token).execute()
        return True
    except Exception as e:
        print(f"Error logging out session: {e}")
        return False

