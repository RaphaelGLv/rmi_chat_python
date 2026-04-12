import random
import socket
import threading
import sys
import os
import time

sys.path.append(os.getcwd())

from server.chat_dispatcher import ChatDispatcher
from shared import chat_protocol
from shared.enums.chat_operations import ChatOperations, get_operation_style
from server.chat_skeleton import ChatSkeleton

class ChatServer:
    MAX_PENDING_ACKS = 10

    def __init__(self, host='0.0.0.0', port=5000):
        self._ack_lock = threading.Lock()
        # Pending ACK Table: { (username, request_id): cached_response }
        self.pending_ack_table = {} 
        self.skeleton = ChatSkeleton()
        self.dispatcher = ChatDispatcher(self.skeleton)
        
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
                
                if op_id == ChatOperations.ACK.value:
                    self._handle_ack_operation(args, user)
                    continue

                style = get_operation_style(op_id)
                random_value = None
                
                if style == "RRA" and user:
                    random_value = random.random()

                    if random_value < 0.25:
                        print("\n")
                        print(f"\033[33m -- PERDA DE PACOTE SIMULADA (REQUISIÇÃO) -- \033[0m")
                        print(f"\033[33m[RRA] Simulando perda de pacote na requisição para {user}: Req {req_id}\033[0m")
                        print(f"\033[33m[RRA] O cliente tentará repetir a chamada e o processo ocorrerá de novo\033[0m")
                        print("\n>")
                        continue
                    elif random_value < 0.50:
                        print("\n")
                        print(f"\033[33m -- TIMEOUT SIMULADO -- \033[0m")
                        print(f"\033[33m[RRA] Simulando atraso de 2,5s na resposta para {user}: Req {req_id}\033[0m")
                        print("\n>")
                        time.sleep(2.5)
                        continue
                    
                    
                    cached_response = self.pending_ack_table.get((user, req_id))
                    if cached_response is not None:
                        self._handle_cached_response(conn, cached_response, user, req_id)
                        continue
                    
                try:
                    response = self.dispatcher.dispatch(op_id, args, context)
                except Exception as e:
                    response = {"status": "error", "message": f"Erro interno do servidor: {e}"}

                if style in ["RR", "RRA"]:
                    if style == "RRA" and user:
                        self._add_to_cache(user, req_id, response)
                        print("-- RESPOSTA ARMAZENADA EM CACHE --")
                        
                    
                    random_value = random.random()

                    if style == "RRA" and user and random_value is not None and random_value < 0.50:
                        print("\n")
                        print(f"\033[33m -- PERDA DE PACOTE SIMULADA (RESPOSTA) -- \033[0m")
                        print(f"\033[33m[RRA] Simulando perda de resposta para {user}: Req {req_id}\033[0m")
                        print(f"\033[33m[RRA] O cliente repetirá a chamada, a resposta estará salva em cache e será retornada sem processamento\033[0m")
                        print("\n>")
                        continue
                    
                    chat_protocol.send_packet(conn, ChatOperations.REPLY.value, {"result": response}, req_id)


            except Exception as e:
                print(f"Erro no cliente {addr}: {e}")
                break
        conn.close()
        
    def _handle_ack_operation(self, args, user):
        ack_req_id = args.get('target_requestId')
        if (user, ack_req_id) in self.pending_ack_table:
            del self.pending_ack_table[(user, ack_req_id)]
            print(f"[ACK] Request {ack_req_id} confirmado por {user}.")
            self._print_cache_table()
            
    def _handle_cached_response(self, conn, cached_response, user, req_id):
        print(f"[REPETIÇÃO] Reenviando resposta cacheada para {user}: Req {req_id}")
        self._print_cache_table()
        chat_protocol.send_packet(conn, ChatOperations.REPLY.value, {"result": cached_response}, req_id)

    def _validate_RRA_idempotency(self, user, req_id):
        return (user, req_id) in self.pending_ack_table
            

    def _add_to_cache(self, user, req_id, response):
        with self._ack_lock:
            if len(self.pending_ack_table) >= self.MAX_PENDING_ACKS:
                oldest_key = next(iter(self.pending_ack_table))
                self.pending_ack_table.pop(oldest_key)
            
        self.pending_ack_table[(user, req_id)] = response
        print(f"[RRA] Aguardando ACK de {user} para req {req_id}")
        self._print_cache_table()

    def _print_cache_table(self):
        with self._ack_lock:
            entries = list(self.pending_ack_table.items())

        print("\n=== TABELA DE CACHE (pending_ack_table) ===")

        if not entries:
            print("(vazia)")
            print("===========================================\n")
            return

        header_user = "Usuario"
        header_req = "RequestId"
        header_status = "Status"

        rows = []
        for (username, req_id), cached_response in entries:
            status = "-"
            if isinstance(cached_response, dict):
                status = str(cached_response.get("status", "-"))
            rows.append((str(username), str(req_id), status))

        user_w = max(len(header_user), *(len(r[0]) for r in rows))
        req_w = max(len(header_req), *(len(r[1]) for r in rows))
        status_w = max(len(header_status), *(len(r[2]) for r in rows))

        sep = f"+-{'-' * user_w}-+-{'-' * req_w}-+-{'-' * status_w}-+"
        print(sep)
        print(f"| {header_user:<{user_w}} | {header_req:<{req_w}} | {header_status:<{status_w}} |")
        print(sep)
        for username, req_id, status in rows:
            print(f"| {username:<{user_w}} | {req_id:<{req_w}} | {status:<{status_w}} |")
        print(sep)
        print("===========================================\n")

if __name__ == "__main__":
    ChatServer()