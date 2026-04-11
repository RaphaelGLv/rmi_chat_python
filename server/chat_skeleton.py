from datetime import datetime
import socket
import sqlite3

class ChatSkeleton:
    DB_NAME = 'chat.db'

    def __init__(self):
        self.active_users = {}
        self.setup_db()
        
    def _get_db_connection(self):
        return sqlite3.connect(self.DB_NAME)

    def setup_db(self):
        try: 
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, message TEXT, timestamp TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
            
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users VALUES (NULL, ?, ?)", ("admin", "123"))
                cursor.execute("INSERT INTO users VALUES (NULL, ?, ?)", ("user", "123"))
                
            conn.commit()
        finally:
            conn.close()

    def login(self, username, password, current_conn):
        if username in self.active_users:
            old_conn = self.active_users[username]
            
            try:
                old_conn.send(b"", socket.MSG_NOSIGNAL)
            except:
                del self.active_users[username]
        
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT username, password FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()

            if user is None:
                return self.register_user(username, password, conn)

            if user[1] != password:
                return None
        finally:
            conn.close()
            
        self.active_users[username] = current_conn
        
        return username

    def register_user(self, username, password, conn=None):
        created_conn = False
        try:
            if conn is None:
                conn = self._get_db_connection()
                created_conn = True
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        finally:
            if created_conn:
                conn.close()
        return username
    
    def list_active_users(self):
        return list(self.active_users.keys())

    def save_message(self, sender, message):
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)', (sender, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        finally:
            conn.close()
            
    def get_history(self):
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT sender, message, timestamp FROM messages ORDER BY id DESC LIMIT 50')
            rows = cursor.fetchall()
        finally:
            conn.close()
        return [{"sender": r[0], "message": r[1], "timestamp": r[2]} for r in reversed(rows)]