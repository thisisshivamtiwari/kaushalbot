import requests
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from config import LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_REDIRECT_URI
from database import db

class LinkedInOAuth:
    def __init__(self):
        self.client_id = LINKEDIN_CLIENT_ID
        self.client_secret = LINKEDIN_CLIENT_SECRET
        self.redirect_uri = LINKEDIN_REDIRECT_URI
        self.auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.profile_url = "https://api.linkedin.com/v2/me"
    
    def get_auth_url(self, state):
        """Generate LinkedIn OIDC authorization URL"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'scope': 'openid profile email'
        }
        
        query = urlencode(params)
        auth_url = f"{self.auth_url}?{query}"
        return auth_url
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(self.token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token exchange failed: {response.text}")
    
    def get_user_profile(self, access_token):
        """Get LinkedIn user profile using OIDC userinfo endpoint"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Use the new OIDC userinfo endpoint
        userinfo_url = "https://api.linkedin.com/v2/userinfo"
        response = requests.get(userinfo_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Profile fetch failed: {response.text}")
    
    def decode_id_token(self, id_token):
        """Decode and validate ID token (JWT)"""
        try:
            # For now, we'll just decode without signature verification
            # In production, you should verify the JWT signature using LinkedIn's JWKS
            import jwt
            decoded = jwt.decode(id_token, options={"verify_signature": False})
            return decoded
        except Exception as e:
            raise Exception(f"ID token decode failed: {e}")
    
    def save_linkedin_connection(self, user_id, access_token, refresh_token, profile_data, id_token=None):
        """Save LinkedIn connection to database"""
        linkedin_data = {
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'profile_data': profile_data,
            'id_token': id_token,
            'connected_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(days=60)  # LinkedIn tokens expire in 60 days
        }
        
        # Update if exists, insert if not
        db.db.linkedin_connections.update_one(
            {'user_id': user_id},
            {'$set': linkedin_data},
            upsert=True
        )
        return True
    
    def get_linkedin_connection(self, user_id):
        """Get LinkedIn connection for user"""
        return db.db.linkedin_connections.find_one({'user_id': user_id})
    
    def is_connected(self, user_id):
        """Check if user has active LinkedIn connection"""
        connection = self.get_linkedin_connection(user_id)
        if not connection:
            return False
        
        # Check if token is expired
        expires_at = connection.get('expires_at')
        if expires_at:
            # Handle both datetime objects and string dates
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    # If we can't parse the date, assume it's expired
                    return False
            
            # Make sure both are timezone-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                return False
        
        return True

# Global LinkedIn OAuth instance
linkedin_oauth = LinkedInOAuth()
