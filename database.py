import sqlite3
import hashlib
import os
import secrets
import time
from typing import Optional, Dict, List

DB_PATH = "app.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            binance_api_key TEXT,
            binance_api_secret TEXT,
            proxy TEXT
        )
        """)
        
        # Добавляем колонку proxy, если её нет (для обратной совместимости)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN proxy TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Временные коды авторизации (для обмена на токен)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_codes (
            code TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        
        # Постоянные токены доступа (Access Tokens)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        
        # История операций
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            timestamp REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        conn.commit()

def hash_password(password: str, salt: bytes) -> str:
    """Хэширование пароля через PBKDF2."""
    key = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt, 
        100000
    )
    return key.hex()

def register_user(username: str, password: str) -> bool:
    """Регистрация нового пользователя."""
    salt = secrets.token_bytes(16)
    pwd_hash = hash_password(password, salt)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, pwd_hash, salt.hex())
            )
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False  # Пользователь уже существует

def verify_user(username: str, password: str) -> Optional[int]:
    """Проверка логина и пароля. Возвращает user_id."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash, salt FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if row:
            user_id, stored_hash, salt_hex = row
            salt = bytes.fromhex(salt_hex)
            if hash_password(password, salt) == stored_hash:
                return user_id
    return None

def update_user_settings(user_id: int, api_key: str, api_secret: str, proxy: str):
    """Сохранение настроек пользователя."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE users SET binance_api_key = ?, binance_api_secret = ?, proxy = ? WHERE id = ?",
            (api_key, api_secret, proxy, user_id)
        )
        conn.commit()

def get_user_settings(user_id: int) -> tuple:
    """Получение настроек пользователя (api_key, api_secret, proxy)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT binance_api_key, binance_api_secret, proxy FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1], row[2]
    return None, None, None

def create_auth_code(user_id: int) -> str:
    """Создает временный auth_code для OAuth."""
    code = secrets.token_urlsafe(32)
    expires_at = time.time() + 600  # 10 минут
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO oauth_codes (code, user_id, expires_at) VALUES (?, ?, ?)", (code, user_id, expires_at))
        conn.commit()
    return code

def exchange_code_for_token(code: str) -> Optional[str]:
    """Обменивает auth_code на постоянный access_token."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, expires_at FROM oauth_codes WHERE code = ?", (code,))
        row = cursor.fetchone()
        
        if row:
            user_id, expires_at = row
            # Удаляем использованный код
            cursor.execute("DELETE FROM oauth_codes WHERE code = ?", (code,))
            
            if time.time() < expires_at:
                # Генерируем токен
                token = secrets.token_urlsafe(64)
                cursor.execute("INSERT INTO oauth_tokens (token, user_id) VALUES (?, ?)", (token, user_id))
                conn.commit()
                return token
        conn.commit()
    return None

def get_user_by_token(token: str) -> Optional[int]:
    """Проверка Bearer токена. Возвращает user_id."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM oauth_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        if row:
            return row[0]
    return None

def log_operation(user_id: int, action: str, details: str = ""):
    """Логирование действий ИИ."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO operations (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, action, details, time.time())
        )
        conn.commit()

def get_history(user_id: int, limit: int = 50) -> List[Dict]:
    """Получение истории операций пользователя."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action, details, timestamp FROM operations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "action": row[0],
                "details": row[1],
                "timestamp": row[2]
            })
        return history

# Инициализируем БД при загрузке модуля
init_db()
