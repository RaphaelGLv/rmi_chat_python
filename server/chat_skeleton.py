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
                            (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, message TEXT)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                            (username TEXT PRIMARY KEY, password TEXT)''')
            
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users VALUES (?, ?)", ("admin", "123"))
                cursor.execute("INSERT INTO users VALUES (?, ?)", ("user", "123"))
                
            conn.commit()
        finally:
            conn.close()

    def login(self, username, password, current_conn):
        if not username or not password:
            return {"status": "error", "message": f"Usuário {username} já está logado."}

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
                return {"status": "error", "message": "Senha inválida."}
        finally:
            conn.close()
            
        self.active_users[username] = current_conn
        
        return {"status": "success", "message": f"Bem-vindo {username}!", "username": username}

    def register_user(self, username, password, conn=None):
        try:
            if conn is None:
                conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        finally:
            conn.close()
        return {"status": "success", "message": f"Usuário {username} registrado com sucesso!"}

    def save_message(self, sender, message):
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (sender, message) VALUES (?, ?)', (sender, message))
            conn.commit()
        finally:
            conn.close()
            
            
    def get_history(self):
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT sender, message FROM messages ORDER BY id DESC LIMIT 50')
            rows = cursor.fetchall()
        finally:
            conn.close()
        return [{"sender": r[0], "message": r[1]} for r in reversed(rows)]