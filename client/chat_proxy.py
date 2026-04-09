from concurrent.futures import ThreadPoolExecutor
import threading
import traceback 
import uuid
import socket
from client.exceptions.request_failed import RequestFailed
from shared import chat_protocol
from shared.enums.chat_operations import ChatOperations, get_operation_style

class ChatProxy:
    _MAX_THREAD_WORKERS = 5
    _MAX_RETRIES = 3
    _TIMEOUT = 2.0

    def __init__(self, host='127.0.0.1', server_port=5000):
        self.host = host
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.server_port))
        
        self.proxy_id = str(uuid.uuid4())[:8]
        self.request_counter = 0

        self._thread_executor = ThreadPoolExecutor(max_workers=self._MAX_THREAD_WORKERS)
        
        self.pending_replies = {}
        self.on_notification = None
        self._lock = threading.Lock()

        self._is_listening = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        
    def stop(self):
        self._is_listening = False
        try:
            self.sock.close()
            self._thread_executor.shutdown(wait=False)
        except Exception as e:
            print(f"[ERRO] Falha ao fechar o proxy: {e}")

    def _generate_new_req_id(self):
        self.request_counter += 1
        return f'{self.proxy_id}:{self.request_counter}'
        
    def _listen_loop(self):
        while self._is_listening:
            try:
                packet = chat_protocol.receive_packet(self.sock)
                if not packet: break
                
                req_id = packet.get('requestId')
                if packet.get('operationId') == ChatOperations.REPLY.value:
                    with self._lock:
                        if req_id in self.pending_replies:
                            entry = self.pending_replies.get(req_id)
                            entry['data'] = packet
                            entry['event'].set()
                            
                elif packet.get('operationId') == ChatOperations.NOTIFICATION.value:
                    if self.on_notification:
                        self.on_notification(packet)
            except: break


    def _do_operation(self, operation_id, args, is_async = False):
        if is_async:
            self._thread_executor.submit(self._do_operation, operation_id, args, False)
        else:
            return self._execute_with_retry(operation_id, args)
        
    def _execute_with_retry(self, operation_id, args):
        req_id = self._generate_new_req_id()
        style = get_operation_style(operation_id)
        
        wait_event = threading.Event()
        with self._lock:
            self.pending_replies[req_id] = {'event': wait_event, 'data': None}

        try:
            for attempt in range(self._MAX_RETRIES):
                try:
                    chat_protocol.send_packet(self.sock, operation_id, args, req_id)
                    
                    if style in ["RR", "RRA"]:
                        if wait_event.wait(timeout=self._TIMEOUT):
                            reply = self.pending_replies[req_id]['data']
                            if style == "RRA":
                                self._send_ack(req_id)
                            return reply.get('args').get('result')
                        raise socket.timeout
                    
                    return {"status": "success"} 
                except (socket.timeout, ConnectionResetError):
                    wait_event.clear()
            
            raise RequestFailed(f"Operação {operation_id} com id = {req_id} falhou após {self._MAX_RETRIES} tentativas.")

        finally:
            with self._lock:
                self.pending_replies.pop(req_id, None)

    def _send_ack(self, target_id):
        chat_protocol.send_packet(self.sock, ChatOperations.ACK.value, 
                                 {"target_requestId": target_id}, target_id)

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