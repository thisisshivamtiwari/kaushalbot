import pymongo
from datetime import datetime
from config import MONGODB_URI

class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(MONGODB_URI)
        self.db = self.client.kaushal_bot
        
    def save_user(self, user_id, username, first_name, last_name=None):
        """Save or update user information"""
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Update if exists, insert if not
        self.db.users.update_one(
            {'user_id': user_id},
            {'$set': user_data},
            upsert=True
        )
        return True
    
    def save_post(self, user_id, content, post_type='text', status='draft', **kwargs):
        """Save a new post with optional AI-generated fields"""
        post_data = {
            'user_id': user_id,
            'content': content,
            'post_type': post_type,
            'status': status,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Add any additional fields passed as kwargs
        post_data.update(kwargs)
        
        result = self.db.posts.insert_one(post_data)
        return str(result.inserted_id)
    
    def get_user_posts(self, user_id, status='draft'):
        """Get user's posts by status"""
        posts = self.db.posts.find(
            {'user_id': user_id, 'status': status}
        ).sort('created_at', -1)
        return list(posts)
    
    def get_user(self, user_id):
        """Get user information"""
        return self.db.users.find_one({'user_id': user_id})

# Global database instance
db = Database()
