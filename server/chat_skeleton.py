import sqlite3

class ChatSkeleton:
    DB_NAME = 'chat.db'

    def __init__(self):
        self.active_users = {}
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, msg TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (username TEXT PRIMARY KEY, password TEXT)''')
        
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users VALUES (?, ?)", ("admin", "123"))
            cursor.execute("INSERT INTO users VALUES (?, ?)", ("user", "123"))
            
        conn.commit()
        conn.close()

    def login(self, username, password):
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        
        query = 'SELECT username FROM users WHERE username = ? AND password = ?'
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        
        conn.close()

        if user is None:
            return {"status": "error", "message": "Usuário ou senha incorretos"}
        
        return {"status": "success", "message": f"Bem-vindo {username}!", "username": username}

    def save_message(self, sender, msg):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (sender, msg) VALUES (?, ?)', (sender, msg))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar mensagem: {e}")
            return False
            
    def get_history(self):
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT sender, msg FROM messages ORDER BY id DESC LIMIT 50')
        rows = cursor.fetchall()
        conn.close()
        return [{"sender": r[0], "msg": r[1]} for r in reversed(rows)]