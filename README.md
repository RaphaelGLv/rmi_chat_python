# Chat Distribuído com RPC/RMI e Threads

Este projeto implementa um sistema de chat distribuído em Python com comunicação via socket, protocolo próprio de requisição-resposta e separação clara entre cliente, proxy, dispatcher e skeleton. A proposta é simular o comportamento de invocação remota de métodos, como em RPC/RMI, para que as operações de chat pareçam chamadas locais, mas sejam executadas no servidor.

O sistema atende ao enunciado do trabalho ao oferecer:

- autenticação simples com usuário e senha;
- broadcast de mensagens;
- mensagens privadas;
- listagem de usuários conectados;
- notificação de entrada e saída;
- identificação de requisições com `requestId` e `operationId`;
- suporte aos estilos de comunicação `R`, `RR` e `RRA`;
- concorrência com threads no servidor e no cliente.

## Objetivo do Trabalho

O documento enviado pede a criação de um chat distribuído em que o cliente não acessa diretamente as operações do servidor. Em vez disso, ele deve chamar métodos de alto nível, como `enviar_mensagem()`, `mensagem_privada()` e `listar_usuarios()`, e essas chamadas precisam ser transformadas em requisições remotas.

Em termos práticos, isso significa:

- o cliente usa uma camada intermediária, o proxy ou stub;
- o servidor usa um dispatcher e um skeleton para receber e executar as operações;
- cada mensagem transporta um identificador de operação e um identificador único de requisição;
- o sistema deve demonstrar concorrência e comunicação assíncrona;
- o funcionamento deve parecer transparente para quem usa o cliente.

## Arquitetura

O projeto foi organizado para refletir a arquitetura clássica de RPC/RMI:

### 1. Cliente

O cliente é a interface usada pelo usuário final. Ele recebe comandos digitados no terminal e os converte em operações remotas. A execução principal está em [client/chat_client.py](client/chat_client.py).

### 2. Proxy / Stub

O proxy fica em [client/chat_proxy.py](client/chat_proxy.py). Ele simula chamadas locais como `login`, `send_global`, `send_private`, `list_users` e `get_history`, mas internamente:

- monta uma requisição;
- atribui `requestId` único;
- envia os dados ao servidor;
- aguarda resposta quando o estilo de comunicação exige isso;
- trata notificações recebidas assincronamente;
- envia ACK quando o modo `RRA` é usado.

### 3. Dispatcher & Skeleton

O dispatcher do servidor está em [server/chat_dispatcher.py](server/chat_dispatcher.py). Ele recebe a operação solicitada, identifica o `operationId` e encaminha a execução para o método correto.

O skeleton está em [server/chat_skeleton.py](server/chat_skeleton.py). Ele concentra o estado do sistema, como usuários autenticados, persistência de mensagens e cadastro de usuários no SQLite.

### 4. Protocolo

O protocolo de comunicação está em [shared/chat_protocol.py](shared/chat_protocol.py). Ele define o formato da mensagem enviada pela rede e implementa o empacotamento com JSON e cabeçalho binário de tamanho fixo.

## Fluxo de Comunicação

O fluxo básico segue o modelo `Request -> Reply`:

1. o cliente monta um pacote com `requestId`, `operationId` e `args`;
2. o proxy envia a requisição ao servidor;
3. o servidor lê o pacote, identifica a operação e executa a rotina adequada;
4. se a operação for síncrona, o servidor responde com um `Reply`;
5. o cliente trata a resposta ou a notificação recebida.

O sistema também suporta notificações do tipo `Notification`, usadas para broadcast, mensagens privadas e avisos de entrada/saída.

## Estilos de Comunicação

O enunciado pede a implementação de pelo menos dois estilos de comunicação. Este projeto cobre três:

- `R` - Request: o cliente envia a operação e não espera resposta direta. É usado em notificações e ACK.
- `RR` - Request-Reply: o cliente envia a requisição e aguarda resposta. É usado em login, listagem de usuários e histórico.
- `RRA` - Request-Reply-Ack: o cliente envia a requisição, recebe a resposta (sem bloquear a execução, de forma assíncrona) e confirma o recebimento com ACK. É usado em mensagens globais e privadas.

Esses estilos são definidos em [shared/enums/chat_operations.py](shared/enums/chat_operations.py).

## Concorrência com Threads

### No Servidor

O servidor é multiusuário e concorrente. A execução principal está em [server/chat_server.py](server/chat_server.py):

- a thread principal aceita conexões;
- para cada cliente conectado, uma nova thread é criada;
- cada thread processa as requisições daquele cliente;
- mensagens são enviadas para outros clientes sem bloquear o fluxo principal.

### No Cliente

O cliente também trabalha de forma assíncrona:

- a thread principal recebe a entrada do usuário e envia comandos;
- uma thread de escuta em background recebe notificações e respostas do servidor.
- uma thread pool com um máximo de 5 _workers_, que são threads locais do cliente para gerenciar as requisições assíncronas (R e RRA) utilizando Locks para garantir a multiplexação segura das mensagens do cliente, permitindo o envio paralelo de múltiplos pacotes através de uma única conexão.

Isso permite continuar digitando enquanto mensagens chegam em paralelo.

## Autenticação

O sistema exige login antes do uso do chat. A autenticação é feita com usuário e senha no método `login`.

Se o usuário não existir, o sistema o cadastra automaticamente na base local. Se a senha estiver incorreta, o acesso é recusado.

## Organização das Pastas

### [client](client)

Camada do usuário e do stub remoto.

- [client/chat_client.py](client/chat_client.py): ponto de entrada do cliente e loop principal de uso;
- [client/chat_proxy.py](client/chat_proxy.py): proxy/stub responsável por transformar chamadas locais em requisições remotas, gerenciando a conexão com o servidor;
- [client/chat_service.py](client/chat_service.py): interpreta comandos digitados no terminal e chama o proxy;
- [client/enums/user_commands.py](client/enums/user_commands.py): lista os comandos aceitos pelo usuário.

### [server](server)

Camada do servidor, com dispatch e persistência.

- [server/chat_server.py](server/chat_server.py): abre o socket, aceita clientes e coordena as threads;
- [server/chat_dispatcher.py](server/chat_dispatcher.py): faz o roteamento da operação para o método correto;
- [server/chat_skeleton.py](server/chat_skeleton.py): concentra a lógica de domínio e conexão com banco de dados;

### [shared](shared)

Elementos compartilhados entre cliente e servidor.

- [shared/chat_protocol.py](shared/chat_protocol.py): serialização e desserialização dos pacotes;
- [shared/enums/chat_operations.py](shared/enums/chat_operations.py): enumeração das operações e estilos de comunicação. Cumpre a função do Java RMI Remote Interface

## Operações Disponíveis

O cliente suporta os seguintes comandos:

- `/g <mensagem>`: envia broadcast para todos os usuários conectados;
- `/p <usuario> <mensagem>`: envia mensagem privada;
- `/usuarios`: lista usuários online;
- `/historico`: recupera as últimas mensagens salvas no servidor;
- `/ajuda`: mostra os comandos disponíveis;
- `/sair`: encerra a sessão do cliente.

## Como o Código Aplica o conceito de RMI

- o cliente chama métodos como `login`, `list_users`, `send_global` e `send_private` no proxy;
- o proxy converte essas chamadas em pacotes remotos;
- o servidor recebe a requisição e usa o dispatcher para escolher a operação;
- o skeleton executa a lógica concreta;
- a resposta volta ao cliente de forma transparente.

Esse desenho separa claramente a interface de uso da execução real da operação.

## Identificação das Requisições

Cada pacote inclui:

- `requestId`: identificador único da requisição;
- `operationId`: nome da operação remota;
- `args`: parâmetros da chamada.

Isso permite controlar respostas, tratar reenvio em caso de timeout e evitar duplicidade especialmente no fluxo `RRA`.

## Execução

O ponto de entrada do servidor é [server/chat_server.py](server/chat_server.py).
O ponto de entrada do cliente é [client/chat_client.py](client/chat_client.py).

### Requisitos

- Python 3+

> _Como o projeto usa apenas bibliotecas padrão do Python, não há dependências externas obrigatórias._

### Como rodar o projeto

1. Clone o repositório

```
git clone https://github.com/RaphaelGLv/rmi_chat_python.git
```

2. Acesse o diretório

```
cd rmi_chat_python/
```

3. Inicie o servidor

```
python -m server.chat_server
```

ou

```
python3 -m server.chat_server
```

4. Abra outros _n_ terminais no mesmo diretório

5. Para cada terminal aberto, inicie um cliente

```
python -m client.chat_client
```

ou

```
python3 -m client.chat_client
```

## Observações Finais

Este projeto foi documentado para deixar explícito o que o enunciado pediu e como cada parte do código atende a esses requisitos. A implementação procura manter a ideia de um sistema distribuído com chamada remota transparente, separação de responsabilidades e concorrência entre múltiplos clientes.
