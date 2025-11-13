import sqlite3
from datetime import datetime

class User:
    def __init__(self, id=None, username=None, password_hash=None, is_admin=False):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
    
    @staticmethod
    def init_db():
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_username(username):
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(id=row[0], username=row[1], password_hash=row[2], is_admin=bool(row[3]))
        return None
    
    def save(self):
        conn = sqlite3.connect('licenses.db')
        cursor = conn.cursor()
        if self.id:
            cursor.execute('''
                UPDATE users SET username=?, password_hash=?, is_admin=? WHERE id=?
            ''', (self.username, self.password_hash, self.is_admin, self.id))
        else:
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)
            ''', (self.username, self.password_hash, self.is_admin))
        conn.commit()
        conn.close()