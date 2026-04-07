import socket
import threading
import sys
import os

sys.path.append(os.getcwd())

from client.chat_proxy import ChatProxy
from client.chat_command_handler import ChatCommandHandler
from shared.enums.chat_operations import ChatOperations
from shared import chat_protocol

class ChatClient:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy = None
        self.is_running = False

    def start(self):
        try:
            self.sock.connect((self.host, self.port))
            self.proxy = ChatProxy(self.sock)
            
            if self._authenticate():
                self.is_running = True
                self._start_listening_thread()
                self._main_loop()
        except Exception as e:
            print(f"Erro ao conectar ao servidor: {e}")
        finally:
            self.stop()

    def _authenticate(self):
        user = input("Usuário: ")
        pwd = input("Senha: ")
        
        res = self.proxy.login(user, pwd)
        
        if res and res.get('status') == "success":
            print(f"\n[SISTEMA] {res.get('message')}")
            return True
        
        print(f"\n[ERRO] Falha no login: {res.get('message') if res else 'Timeout'}")
        return False

    def _start_listening_thread(self):
        thread = threading.Thread(target=self._listen_server, daemon=True)
        thread.start()

    def _listen_server(self):
        while self.is_running:
            try:
                data = chat_protocol.receive_packet(self.sock)
                if not data:
                    break
                
                if data.get('operationId') == ChatOperations.NOTIFICATION.value:
                    sender = data['args'].get('from')
                    content = data['args'].get('content')
                    print(f"\n[{sender}]: {content}")
                    print("> ", end="", flush=True)

            except Exception:
                break
        
        if self.is_running:
            print("\n[SISTEMA] Conexão com o servidor perdida.")
            self.is_running = False

    def _main_loop(self):
        handler = ChatCommandHandler(self.proxy)
        handler._show_help(None)

        while self.is_running:
            try:
                text = input("> ").strip()
                if not text: continue

                result = handler.execute(text)
                
                if result == "EXIT":
                    self.is_running = False

            except ValueError as e:
                print(e)
            except Exception as e:
                print(f"\n[ERRO] Falha na operação: {e}")

    def stop(self):
        self.is_running = False
        self.sock.close()
        print("[SISTEMA] Chat encerrado.")

if __name__ == "__main__":
    client = ChatClient()
    client.start()