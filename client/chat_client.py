import sys
import os

from client.exceptions.request_failed import RequestFailed

sys.path.append(os.getcwd())

from client.chat_proxy import ChatProxy
from client.chat_service import ChatService

class ChatClient:
    def __init__(self):
        self.proxy = None
        self.chat_service = None
        self.is_running = False

    def start(self):
        try:
            self.proxy = ChatProxy()
            self.chat_service = ChatService(self.proxy)
            
            self.proxy.on_notification = self._display_notification
            
            while not self.is_running:
                try:
                    if self._authenticate():
                        self.is_running = True
                except RequestFailed as e:
                    print(f"\n[ERRO] {e}")
                    print("[DICA] Verifique suas credenciais ou tente novamente.")

            self._main_loop()

        except KeyboardInterrupt:
            print("\n[SISTEMA] Encerrando por solicitação do usuário.")
        except Exception as e:
            print(f"\n[ERRO CRÍTICO] Falha na conexão: {e}")
        finally:
            self.stop()

    def _authenticate(self):
        user = input("Usuário: ")
        pwd = input("Senha: ")
        
        res = self.proxy.login(user, pwd)
        
        if res and res.get('status') == "success":
            print(f"\n[SISTEMA] {res.get('message')}")
            self.chat_service.set_logged_in_user(user)
            return True
        
        print(f"\n[ERRO] Falha no login: {res.get('message') if res else 'Timeout'}")
        return False

    def _display_notification(self, data):
        sender = data['args'].get('from')
        content = data['args'].get('content')
        print(f"\n[{sender}]: {content}")
        print("> ", end="", flush=True)

    def _main_loop(self):
        self.chat_service._show_help(None)

        while self.is_running:
            try:
                text = input("> ").strip()
                if not text: continue

                result = self.chat_service.execute(text)
                
                if result == "EXIT":
                    self.is_running = False

            except ValueError as e:
                print(e)
            except Exception as e:
                print(f"\n[AVISO] Não foi possível completar a ação: {e}")
                print("[DICA] Verifique sua conexão ou tente o comando novamente.")

    def stop(self):
        self.is_running = False
        if self.proxy:
            self.proxy.stop()
        print("[SISTEMA] Chat encerrado.")

if __name__ == "__main__":
    client = ChatClient()
    client.start()