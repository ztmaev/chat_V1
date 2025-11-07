"""
Hyptrb API Integration Module
Handles all interactions with the Hyptrb API for user profile fetching
"""
import requests
from typing import Optional, Dict

HYPTRB_BASE_URL = "https://api.hyptrb.africa/"

# Admin role types
ADMIN_ROLES = ['main_admin', 'billing_admin', 'campaign_admin']

def is_admin_role(role):
    """
    Check if a role is any type of admin role
    
    Args:
        role: Role string to check
        
    Returns:
        bool: True if role is main_admin, billing_admin, or campaign_admin
    """
    return role in ADMIN_ROLES

class HyptrbAPIError(Exception):
    """Custom exception for Hyptrb API errors"""
    pass

def fetch_user_role(email: str) -> Optional[Dict]:
    """
    Fetch user role from Hyptrb API
    
    Args:
        email: User's email address
        
    Returns:
        Dict with user role information or None if not found
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}roles/{email}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch user role: {response.status_code}")
        
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching user role: {str(e)}")

def fetch_client_profile(email: str) -> Optional[Dict]:
    """
    Fetch client profile from Hyptrb API
    
    Args:
        email: Client's email address
        
    Returns:
        Dict with client profile information or None if not found
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}clients/get/{email}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch client profile: {response.status_code}")
        
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching client profile: {str(e)}")

def fetch_admin_profile(email: str) -> Optional[Dict]:
    """
    Fetch admin profile from Hyptrb API
    
    Args:
        email: Admin's email address
        
    Returns:
        Dict with admin profile information or None if not found
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}admin/profile/{email}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch admin profile: {response.status_code}")
        
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching admin profile: {str(e)}")

def fetch_influencer_profile(influencer_uid: str) -> Optional[Dict]:
    """
    Fetch influencer profile from Hyptrb API
    
    Args:
        influencer_uid: Influencer's unique identifier
        
    Returns:
        Dict with influencer profile information or None if not found
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}influencer/get/profile/{influencer_uid}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return None
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch influencer profile: {response.status_code}")
        
        data = response.json()
        # Extract data from success response wrapper if present
        if data.get('success') and 'data' in data:
            return data['data']
        return data
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching influencer profile: {str(e)}")

def fetch_user_profile_by_role(email: str, role: str, influencer_uid: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch user profile based on their role
    
    Args:
        email: User's email address
        role: User's role (client, main_admin, billing_admin, campaign_admin, or influencer)
        influencer_uid: Required for influencer role
        
    Returns:
        Dict with user profile information or None if not found
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    if role == 'client':
        return fetch_client_profile(email)
    elif is_admin_role(role):
        return fetch_admin_profile(email)
    elif role == 'influencer':
        if not influencer_uid:
            raise HyptrbAPIError("influencer_uid is required for influencer role")
        return fetch_influencer_profile(influencer_uid)
    else:
        raise HyptrbAPIError(f"Unknown role: {role}")

def extract_display_name(profile: Dict, role: str) -> str:
    """
    Extract display name from profile based on role
    
    Args:
        profile: Profile data from Hyptrb API
        role: User's role
        
    Returns:
        Display name string
    """
    if role == 'client':
        return profile.get('businessName', 'Unknown Client')
    elif is_admin_role(role):
        return profile.get('name', profile.get('email', 'Unknown Admin'))
    elif role == 'influencer':
        return profile.get('full_name', 'Unknown Influencer')
    else:
        return 'Unknown User'

def fetch_client_campaigns(client_email: str) -> list:
    """
    Fetch all campaigns for a client from Hyptrb API
    
    Args:
        client_email: Client's email address
        
    Returns:
        List of campaign dictionaries
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}clients/get/all/campaigns/{client_email}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            return []
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch client campaigns: {response.status_code}")
        
        response_data = response.json()
        
        # Response is paginated with structure: {"data": [...], "total": N, "page": 1, "limit": 10}
        if isinstance(response_data, dict) and 'data' in response_data:
            campaigns = response_data.get('data', [])
            return campaigns if isinstance(campaigns, list) else []
        
        # Fallback for direct array response (backwards compatibility)
        return response_data if isinstance(response_data, list) else []
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching client campaigns: {str(e)}")

def fetch_influencer_collaborations(influencer_uid: str, page: int = 1, limit: int = 100) -> Dict:
    """
    Fetch collaborations (campaigns) for an influencer from Hyptrb API
    
    Args:
        influencer_uid: Influencer's unique identifier
        page: Page number for pagination (default: 1)
        limit: Number of results per page (default: 100 to get all)
        
    Returns:
        Dict with current_clients and past_clients, each containing campaign info
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}influencer/get/clients/collaborations/{influencer_uid}"
        params = {'page': page, 'limit': limit}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            return {'current_clients': [], 'past_clients': []}
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch influencer collaborations: {response.status_code}")
        
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching influencer collaborations: {str(e)}")

def fetch_influencer_jobs(influencer_uid: str, page: int = 1) -> Dict:
    """
    Fetch jobs/campaigns for an influencer from Hyptrb API
    
    Args:
        influencer_uid: Influencer's unique identifier
        page: Page number for pagination (default: 1)
        
    Returns:
        Dict with job information including:
        - influencer_uid: Influencer's UID
        - totalJobs: Total number of jobs
        - totalPages: Total number of pages
        - currentPage: Current page number
        - jobs: List of job objects with campaign details, status, rates, etc.
        
    Raises:
        HyptrbAPIError: If API request fails
    """
    try:
        url = f"{HYPTRB_BASE_URL}influencer/get/jobs/{influencer_uid}"
        params = {'page': page}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            return {
                'influencer_uid': influencer_uid,
                'totalJobs': 0,
                'totalPages': 0,
                'currentPage': page,
                'jobs': []
            }
        
        if response.status_code != 200:
            raise HyptrbAPIError(f"Failed to fetch influencer jobs: {response.status_code}")
        
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HyptrbAPIError(f"Network error fetching influencer jobs: {str(e)}")
