from shared import chat_protocol
from shared.enums.chat_operations import ChatOperations


class ChatDispatcher:
    _SERVER_REQUEST_ID = "SERVER_REQ"
    
    def __init__(self, skeleton):
        self._skeleton = skeleton
        
        self._dispatch_table = {
            ChatOperations.LOGIN.value: self._handle_login,
            ChatOperations.LIST_USERS.value: self._handle_list_users,
            ChatOperations.GET_HISTORY.value: self._handle_get_history,
            ChatOperations.SEND_GLOBAL.value: self._handle_send_global,
            ChatOperations.SEND_PRIVATE.value: self._handle_send_private,
            ChatOperations.ACK.value: self._handle_ack,
        }
        
    def dispatch(self, op_id, args, context):
        handler = self._dispatch_table.get(op_id)
        if handler is None:
            return {"status": "error", "message": "Operação inválida"}
        return handler(args, context)
        
    def _handle_ack(self, args, context):
        user = context["current_user"]
        req_id = args.get('target_requestId')
        if (user, req_id) in self.pending_ack_table:
            del self.pending_ack_table[(user, req_id)]
            print(f"[ACK] Limpo da tabela: Req {req_id} de {user}")
        return None

    def _handle_login(self, args, context):
        username = args.get('username')
        password = args.get('password')
        
        if not username or not password:
            return {"status": "error", "message": f"Usuário {username} já está logado."}
        
        res = self._skeleton.login(username, password, context["conn"])
        
        if res == None:
            return {"status": "error", "message": "Senha inválida."}
        
        context["current_user"] = username
        self._skeleton.active_users[context["current_user"]] = context["conn"]
        
        return {"status": "success", "message": f"Bem-vindo {username}!", "username": username}


    def _handle_send_global(self, args, context):
        user = context["current_user"]
        content = args.get('content')
        self._skeleton.save_message(user, content)

        for username, sock in self._skeleton.active_users.items():
            if username == user: continue
            
            chat_protocol.send_packet(sock, ChatOperations.NOTIFICATION.value, 
                                    {"from": user, "content": content}, self._SERVER_REQUEST_ID)
        return {"status": "success", "message": "Mensagem global enviada com sucesso."}

    def _handle_send_private(self, args, context):
        sender = context["current_user"]
        target, content = args.get('to'), args.get('content')
        if target in self._skeleton.active_users:
            chat_protocol.send_packet(self._skeleton.active_users[target], 
                                    ChatOperations.NOTIFICATION.value, 
                                    {"from": f"{sender} (P)", "content": content}, self._SERVER_REQUEST_ID)
            return {"status": "success", "message": "Mensagem privada enviada com sucesso."}
        return {"status": "error", "message": f"Falha ao enviar mensagem privada: usuário '{target}'. Usuário não encontrado ou offline."}

    def _handle_list_users(self, args, context):
        active_users = self._skeleton.list_active_users()
        return {"status": "success", "users": active_users}

    def _handle_get_history(self, args, context):
        message_history = self._skeleton.get_history()
        return {"status": "success", "messages": message_history}
