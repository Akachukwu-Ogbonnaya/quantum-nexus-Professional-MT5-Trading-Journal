# models/user.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from app.utils.database import get_db_connection

class User(UserMixin):
    def __init__(self, id_, username, password_hash, email=None, preferences=None):
        self.id = id_
        self.username = username
        self.password_hash = password_hash
        self.email = email
        self.preferences = preferences or {}

    @staticmethod
    def _get_user_from_row(row, cursor):
        """Helper method to extract user data from database row"""
        if not row:
            return None
            
        # Convert to dict for consistent access
        if hasattr(cursor, 'db_type') and cursor.db_type == 'postgresql':
            user_data = dict(row)
        else:
            user_data = dict(zip([col[0] for col in cursor.description], row))
        
        # Parse preferences JSON
        prefs = user_data.get('preferences', '{}')
        if prefs and prefs != '{}':
            try:
                preferences = json.loads(prefs)
            except:
                preferences = {}
        else:
            preferences = {}
        
        return User(
            user_data['id'], 
            user_data['username'], 
            user_data['password_hash'], 
            user_data.get('email'), 
            preferences
        )

    @staticmethod
    def get(user_id):
        """Get user by ID - hybrid compatible"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Database-specific query
            if hasattr(conn, 'db_type') and conn.db_type == 'postgresql':
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE id = %s', (user_id,))
            else:
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE id = ?', (user_id,))
            
            row = cursor.fetchone()
            return User._get_user_from_row(row, cursor)
            
        except Exception as e:
            print(f"User.get error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def get_by_username(username):
        """Get user by username - hybrid compatible"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Database-specific query
            if hasattr(conn, 'db_type') and conn.db_type == 'postgresql':
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE username = %s', (username,))
            else:
                cursor.execute('SELECT id, username, password_hash, email, preferences FROM users WHERE username = ?', (username,))
            
            row = cursor.fetchone()
            return User._get_user_from_row(row, cursor)
            
        except Exception as e:
            print(f"User.get_by_username error: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def create(username, password, email=None):
        """Create new user - hybrid compatible"""
        password_hash = generate_password_hash(password)
        preferences = json.dumps({'theme': 'dark', 'notifications': True})

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if hasattr(conn, 'db_type') and conn.db_type == 'postgresql':
                # PostgreSQL uses %s placeholders and RETURNING id
                cursor.execute(
                    'INSERT INTO users (username, password_hash, email, preferences) VALUES (%s, %s, %s, %s) RETURNING id',
                    (username, password_hash, email, preferences)
                )
                user_id = cursor.fetchone()[0]
            else:
                # SQLite uses ? placeholders and lastrowid
                cursor.execute(
                    'INSERT INTO users (username, password_hash, email, preferences) VALUES (?, ?, ?, ?)',
                    (username, password_hash, email, preferences)
                )
                user_id = cursor.lastrowid
            
            conn.commit()
            return User(user_id, username, password_hash, email, json.loads(preferences))
            
        except Exception as e:
            conn.rollback()
            # Handle unique constraint violation for both databases
            error_msg = str(e).lower()
            if 'unique' in error_msg or 'duplicate' in error_msg:
                print(f"Username already exists: {username}")
                return None
            else:
                print(f"Database error in User.create: {e}")
                return None
        finally:
            conn.close()

    def update_last_login(self):
        """Update last login timestamp - hybrid compatible"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if hasattr(conn, 'db_type') and conn.db_type == 'postgresql':
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s', (self.id,))
            else:
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (self.id,))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error updating last login: {e}")
        finally:
            conn.close()

    def check_password(self, password):
        """Check if provided password matches stored hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'preferences': self.preferences
        }

    def __repr__(self):
        return f"<User {self.username}>"