import sqlite3
from flask_login import UserMixin
from werkzeug.security import check_password_hash,generate_password_hash

DATABASE = 'dbpfe5.db'

class User(UserMixin):
    def __init__(self, id, username, password, is_admin, can_upload_multiple):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin
        self.can_upload_multiple = can_upload_multiple

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Users WHERE ID = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['ID'], user['Username'], user['Password'], user['IsAdmin'], user['CanUploadMultiple'])
    return None

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM Users WHERE Username = ?', (username,)).fetchone()
    conn.close()
    if user:
        return User(user['ID'], user['Username'], user['Password'], user['IsAdmin'], user['CanUploadMultiple'])
    return None

def add_user(username, password):
    conn = get_db_connection()
    hashed_password = generate_password_hash(password)
    try:
        conn.execute('INSERT INTO Users (Username, Password, IsAdmin, CanUploadMultiple) VALUES (?, ?, ?, ?)', 
                     (username, hashed_password, 0, 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
