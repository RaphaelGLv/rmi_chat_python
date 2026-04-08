import traceback 
import uuid
import socket
from client.exceptions.request_failed import RequestFailed
from shared import chat_protocol
from shared.enums.chat_operations import ChatOperations, get_operation_style

class ChatProxy:
    MAX_RETRIES = 3
    TIMEOUT = 2.0
    
    def __init__(self, sock):
        self.sock = sock
        self.proxy_id = str(uuid.uuid4())[:8]
        self.request_counter = 0

    def _handle_new_request(self):
        self.request_counter += 1
        self.current_req_id = f'{self.proxy_id}:{self.request_counter}'


    def _do_operation(self, operation_id, args):
        self._handle_new_request()
        style = get_operation_style(operation_id)
        
        self.sock.settimeout(self.TIMEOUT)

        for attempt in range(self.MAX_RETRIES):
            try:
                chat_protocol.send_packet(self.sock, operation_id, args, self.current_req_id)

                if style in ["RR", "RRA"]:
                    reply = chat_protocol.receive_packet(self.sock)
                    
                    if reply is None:
                        raise ConnectionResetError("Servidor fechou a conexão")

                    if style == "RRA":
                        ack_args = {"target_requestId": self.current_req_id}
                        chat_protocol.send_packet(self.sock, ChatOperations.ACK.value, 
                                                ack_args, self.current_req_id)
                    
                    self.sock.settimeout(None)
                    return reply.get('args').get('result')
                
                self.sock.settimeout(None)
                return {"status": "success", "message": "Enviado (Estilo R)"}

            except (socket.timeout, ConnectionResetError) as e:
                print(f" [RETRY] Falha de rede ({e}). Tentativa {attempt + 1}...")
                if attempt == self.MAX_RETRIES - 1:
                    break 
            except Exception as e:
                print("\n--- ERRO INTERNO NO PROXY ---")
                traceback.print_exc() 
                break 

        self.sock.settimeout(None)
        raise RequestFailed(f"Operação {operation_id} falhou após {self.MAX_RETRIES} tentativas.")

    # --- Chamadas Remotas Transparentes ---

    def login(self, username, password):
        self.username = username 
        return self._do_operation(ChatOperations.LOGIN.value, 
                                 {"username": username, "password": password})

    def list_users(self):
        return self._do_operation(ChatOperations.LIST_USERS.value, {})

    def get_history(self):
        return self._do_operation(ChatOperations.GET_HISTORY.value, {})

    def send_global(self, message):
        return self._do_operation(ChatOperations.SEND_GLOBAL.value, 
                                 {"content": message})

    def send_private(self, to_user, message):
        return self._do_operation(ChatOperations.SEND_PRIVATE.value, 
                                 {"to": to_user, "content": message})