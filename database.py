import sqlite3
import os
import uuid
from typing import Optional, Tuple

DB_PATH = "app.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                client_id TEXT PRIMARY KEY,
                client_secret TEXT,
                token TEXT,
                api_key TEXT,
                api_secret TEXT,
                proxy TEXT
            )
        ''')
        conn.commit()

def register_or_verify_client(client_id: str, client_secret: str) -> Optional[str]:
    """
    Registers a new client or verifies an existing one.
    Returns a new token on success, or None on failure (wrong password).
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT client_secret, token FROM users WHERE client_id = ?', (client_id,))
        row = cursor.fetchone()
        
        new_token = str(uuid.uuid4())
        
        if row is None:
            # New user, register them
            cursor.execute('''
                INSERT INTO users (client_id, client_secret, token) 
                VALUES (?, ?, ?)
            ''', (client_id, client_secret, new_token))
            conn.commit()
            return new_token
        else:
            # Existing user, check password
            db_secret, db_token = row
            if db_secret == client_secret:
                # Issue a new token or use the old one. Let's issue a new one for security.
                cursor.execute('UPDATE users SET token = ? WHERE client_id = ?', (new_token, client_id))
                conn.commit()
                return new_token
            else:
                # Wrong password
                return None

def get_client_id_by_token(token: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT client_id FROM users WHERE token = ?', (token,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return None

def save_settings(client_id: str, api_key: str, api_secret: str, proxy: Optional[str] = None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET api_key = ?, api_secret = ?, proxy = ?
            WHERE client_id = ?
        ''', (api_key, api_secret, proxy, client_id))
        conn.commit()

def get_settings(client_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT api_key, api_secret, proxy FROM users WHERE client_id = ?', (client_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1], row[2]
        return None, None, None

def delete_settings(client_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET api_key = NULL, api_secret = NULL, proxy = NULL
            WHERE client_id = ?
        ''', (client_id,))
        conn.commit()

# Initialize database on module import
init_db()
