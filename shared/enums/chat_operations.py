from enum import Enum

class ChatOperations(Enum):
    LOGIN = "login"
    SEND_GLOBAL = "send_global"
    SEND_PRIVATE = "send_private"
    LIST_USERS = "list_users"
    GET_HISTORY = "get_history"
    NOTIFICATION = "notification"
    REPLY = "reply"
    ACK = 'ack'

def get_operation_style(op_id):
    mapping = {
        ChatOperations.LOGIN.value: "RR",
        ChatOperations.LIST_USERS.value: "RR",
        ChatOperations.GET_HISTORY.value: "RR",
        ChatOperations.SEND_GLOBAL.value: "RRA",
        ChatOperations.SEND_PRIVATE.value: "RRA",
        ChatOperations.ACK.value: "R",
        ChatOperations.NOTIFICATION.value: "R"
    }
    return mapping.get(op_id, "RR")