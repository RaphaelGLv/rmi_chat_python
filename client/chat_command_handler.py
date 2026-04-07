from client.enums.user_commands import UserCommands

class ChatCommandHandler:
    def __init__(self, proxy):
        self.proxy = proxy
        self._commands = {
            UserCommands.SAIR: self._cmd_sair,
            UserCommands.USUARIOS: self._cmd_usuarios,
            UserCommands.PRIVADO: self._cmd_privado,
            UserCommands.GLOBAL: self._cmd_global,
            UserCommands.HISTORICO: self._cmd_historico,
            UserCommands.AJUDA: self._show_help
        }

    def execute(self, user_input):
        if not user_input.startswith("/"):
            print("[SISTEMA] Para enviar mensagens, use /g <mensagem> ou /p <usuario> <mensagem>")
            return None

        parts = user_input.split(" ", 2)
        cmd_str = parts[0].lower()

        try:
            command = UserCommands(cmd_str)
            return self._commands[command](parts)
        except (ValueError, KeyError):
            raise ValueError(f"[ERRO] O comando '{cmd_str}' não existe. Digite /ajuda para ver a lista.")

    def _cmd_global(self, parts):
        if len(parts) < 2:
            print("[ERRO] Uso correto: /g <mensagem>")
            return
        content = " ".join(parts[1:]) 
        return self.proxy.send_global(content)

    # --- Métodos de Comando ---

    def _cmd_sair(self, _):
        print("[SISTEMA] Saindo...")
        return "EXIT"

    def _cmd_usuarios(self, _):
        users = self.proxy.list_users()
        print(f"\n[SISTEMA] Usuários online: {', '.join(users.get('users', []))}")

    def _cmd_privado(self, parts):
        if len(parts) < 3:
            print("[ERRO] Uso correto: /p <usuario> <mensagem>")
            return
        target, msg = parts[1], parts[2]
        self.proxy.send_private(target, msg)

    def _cmd_historico(self, _):
        history = self.proxy.get_history()
        print("\n--- HISTÓRICO DE MENSAGENS ---")
        for entry in history:
            print(f"{entry['timestamp']} | {entry['user']}: {entry['content']}")

    def _show_help(self, _=None):
        print("\n" + "—"*40)
        print("  SISTEMA DE MENSAGERIA RMI - COMANDOS")
        print("—"*40)
        
        menu = [
            (UserCommands.GLOBAL.value, "<msg>", "Envia mensagem para todos"),
            (UserCommands.PRIVADO.value, "<user> <msg>", "Mensagem privada para um usuário"),
            (UserCommands.USUARIOS.value, "", "Lista usuários online"),
            (UserCommands.HISTORICO.value, "", "Recupera histórico do servidor"),
            (UserCommands.AJUDA.value, "", "Mostra este menu"),
            (UserCommands.SAIR.value, "", "Encerra sua sessão")
        ]

        for cmd, args, desc in menu:
            print(f" {cmd:<10} {args:<15} | {desc}")
            
        print("—"*40 + "\n")

    def _get_description(self, cmd):
        descriptions = {
            UserCommands.SAIR: "Encerra o chat",
            UserCommands.USUARIOS: "Lista quem está online",
            UserCommands.PRIVADO: "Mensagem privada (/p nick msg)",
            UserCommands.HISTORICO: "Mostra mensagens antigas",
            UserCommands.AJUDA: "Mostra este menu"
        }
        return descriptions.get(cmd, "")