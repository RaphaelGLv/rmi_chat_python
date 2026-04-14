import json
import struct
import socket

def send_packet(sock, operation_id, args, request_id):
    packet = {
        "requestId": request_id,
        "operationId": operation_id,
        "args": args or {}
    }
    try:
        data = json.dumps(packet).encode('utf-8')
        # Header de 4 bytes (Big-endian unsigned int) com o tamanho do JSON
        header = struct.pack('!I', len(data))
        sock.sendall(header + data)
    except Exception as e:
        print(f"[PROTOCOL ERROR] Erro ao enviar: {e}")
        raise

def receive_packet(sock):
    """
    Lê o header de tamanho e garante a recepção do JSON completo.
    """
    try:
        header = sock.recv(4)
        if not header: 
            return None
            
        length = struct.unpack('!I', header)[0]
        
        chunks = []
        bytes_received = 0
        while bytes_received < length:
            chunk = sock.recv(min(length - bytes_received, 4096))
            if not chunk:
                raise ConnectionError("Socket fechado durante a recepção dos dados.")
            chunks.append(chunk)
            bytes_received += len(chunk)
            
        data = b"".join(chunks)
        return json.loads(data.decode('utf-8'))
        
    except socket.timeout:
        # Importante: repassa o timeout para o Stub tratar
        raise
    except Exception as e:
        print(f"[PROTOCOL ERROR] Erro na recepção: {e}")
        return None