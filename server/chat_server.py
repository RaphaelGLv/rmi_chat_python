import socket
import threading
import sys
import os

sys.path.append(os.getcwd())

from shared import chat_protocol
from shared.enums.chat_operations import ChatOperations, get_operation_style
from server.chat_skeleton import ChatSkeleton

class ChatServer:
    MAX_PENDING_ACKS = 10

    def __init__(self, host='0.0.0.0', port=5000):
        # Pending ACK Table: { (username, request_id): status }
        self.pending_ack_table = {} 
        self.skeleton = ChatSkeleton()
        
        self.dispatch_table = {
            ChatOperations.LOGIN.value: self._handle_login,
            ChatOperations.LIST_USERS.value: self._handle_list_users,
            ChatOperations.GET_HISTORY.value: self._handle_get_history,
            ChatOperations.SEND_GLOBAL.value: self._handle_send_global,
            ChatOperations.SEND_PRIVATE.value: self._handle_send_private,
            ChatOperations.ACK.value: self._handle_ack,
        }
        
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        print(f"Servidor RMI (R/RR/RRA) aguardando em {host}:{port}...")
        self._accept_connections()

    def _accept_connections(self):
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        context = {"current_user": None, "conn": conn}
        
        while True:
            try:
                request = chat_protocol.receive_packet(conn)
                if not request: break
                
                op_id = request.get('operationId')
                args = request.get('args', {})
                req_id = request.get('requestId')
                user = context["current_user"]

                style = get_operation_style(op_id)
                
                if style == "RRA" and user:
                    self._validate_RRA_idempotency(user, req_id, conn)
                    continue

                handler = self.dispatch_table.get(op_id)
                if handler is None:
                    response = {"status": "error", "message": "Operação inválida"}
                else:
                    try:
                       response = handler(args, context)
                    except Exception as e:
                        response = {"status": "error", "message": f"Erro interno do servidor: {e}"}

                if style in ["RR", "RRA"]:
                    chat_protocol.send_packet(conn, "reply", {"result": response}, req_id)
                    
                    if style == "RRA" and user:
                        self._add_request_to_pending_ack_table(user, req_id, conn)

            except Exception as e:
                print(f"Erro no cliente {addr}: {e}")
                break
        conn.close()

    # Handlers
    def _handle_ack(self, args, context):
        user = context["current_user"]
        req_id = args.get('target_requestId')
        if (user, req_id) in self.pending_ack_table:
            del self.pending_ack_table[(user, req_id)]
            print(f"[ACK] Limpo da tabela: Req {req_id} de {user}")
        return None

    def _handle_login(self, args, context):
        res = self.skeleton.login(args.get('username'), args.get('password'), context["conn"])
        if res['status'] == "success":
            context["current_user"] = args.get('username')
            self.skeleton.active_users[context["current_user"]] = context["conn"]
        return res

    def _handle_send_global(self, args, context):
        user = context["current_user"]
        content = args.get('content')
        self.skeleton.save_message(user, content)
        for name, sock in self.skeleton.active_users.items():
            chat_protocol.send_packet(sock, ChatOperations.NOTIFICATION.value, 
                                    {"from": user, "content": content})
        return "Mensagem enviada"

    def _handle_send_private(self, args, context):
        sender = context["current_user"]
        target, content = args.get('to'), args.get('content')
        if target in self.skeleton.active_users:
            chat_protocol.send_packet(self.skeleton.active_users[target], 
                                    ChatOperations.NOTIFICATION.value, 
                                    {"from": f"{sender} (P)", "content": content})
            return {"status": "success"}
        return {"status": "error", "message": "Offline"}

    def _handle_list_users(self, args, context):
        return {"users": list(self.skeleton.active_users.keys())}

    def _handle_get_history(self, args, context):
        return self.skeleton.get_history()

    # Utils
    def _validate_RRA_idempotency(self, user, req_id, conn):
        if (user, req_id) in self.pending_ack_table:
            print(f"[REPETIÇÃO] Request {req_id} já processado para {user}. Ignorando execução.")
            chat_protocol.send_packet(conn, "reply", {"result": "OK (Já processado)"}, req_id)

    def _add_request_to_pending_ack_table(self, user, req_id, conn):
        if len(self.pending_ack_table) >= self.MAX_PENDING_ACKS:
            oldest_key = next(iter(self.pending_ack_table))
            self.pending_ack_table.pop(oldest_key)
        
        self.pending_ack_table[(user, req_id)] = True
        print(f"[RRA] Aguardando ACK de {user} para req {req_id}")

if __name__ == "__main__":
    ChatServer()