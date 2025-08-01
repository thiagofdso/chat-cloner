# Documentação Técnica do Clonechat

## Visão Geral

O Clonechat é uma ferramenta avançada para automação do Telegram com duas funcionalidades principais:

1. **Clonagem de Chats**: Permite clonar canais e grupos do Telegram para novos destinos.
2. **Publicação de Pastas Locais**: Implementa o workflow "Zimatise" para processar e publicar conteúdo de pastas locais no Telegram.

## Estrutura do Projeto

```
clonechat/
├── data/
│   ├── clonechat.db         # Banco de dados SQLite
│   │   ├── SyncTasks        # Tarefas de clonagem
│   │   ├── DownloadTasks    # Tarefas de download
│   │   └── PublishTasks     # Tarefas de publicação
│   ├── downloads/           # Arquivos temporários e áudio extraído
│   │   └── -100123456789 - Nome do Canal/
│   │       ├── 2-video.mp4  # Vídeo original (apagado após upload)
│   │       ├── 2-video.mp3  # Áudio extraído (PRESERVADO)
│   │       └── ...
│   └── app.log              # Logs da aplicação
│   └── project_workspace/   # Pasta de trabalho para o pipeline de publicação
├── clonechat/               # Pacote do código-fonte
│   ├── __init__.py
│   ├── cli.py               # Interface de linha de comando
│   ├── config.py            # Gerenciamento de configuração
│   ├── database.py          # Camada de acesso a dados
│   ├── engine.py            # Motor principal de clonagem
│   ├── processor.py         # Processamento de mensagens
│   ├── logging_config.py    # Configuração de logging
│   ├── retry_utils.py       # Utilitários de retry
│   ├── zimatise_one.py      # Implementação do workflow Zimatise
│   └── tasks/
│       ├── __init__.py
│       └── publish_pipeline.py  # Pipeline de publicação
├── links_canais.txt         # Links dos canais clonados
├── main.py                  # Ponto de entrada
├── pyproject.toml           # Configuração do projeto
├── requirements.txt         # Dependências do projeto
└── .env.example             # Exemplo de configuração de ambiente
```

## Componentes Principais

### 1. Módulos Centrais

#### `main.py`

Ponto de entrada principal da aplicação. Inicializa a CLI e direciona para os comandos apropriados.

#### `cli.py`

Implementa a interface de linha de comando usando a biblioteca Typer. Define os comandos disponíveis:

- `sync`: Para clonagem de chats
- `download`: Para download de vídeos
- `publish`: Para o pipeline Zimatise
- Comandos auxiliares: `list-chats`, `test-resolve`, `list-topics`, etc.

#### `config.py`

Gerencia a configuração da aplicação:

- Carrega variáveis de ambiente do arquivo `.env`
- Define constantes e configurações padrão
- Gerencia credenciais do Telegram (API ID, API Hash)

#### `database.py`

Camada de acesso a dados que gerencia o banco de dados SQLite:

- Define o schema das tabelas (`SyncTasks`, `DownloadTasks`, `PublishTasks`)
- Fornece funções para CRUD de tarefas
- Implementa funções para rastrear o progresso das operações

#### `engine.py`

Motor principal para a funcionalidade de clonagem:

- Implementa a lógica de clonagem de chat-para-chat
- Gerencia as estratégias de clonagem (`forward` e `download_upload`)
- Coordena o processamento de mensagens

#### `processor.py`

Processa mensagens individuais do Telegram:

- Implementa a lógica para cada tipo de mídia (texto, foto, vídeo, etc.)
- Gerencia o download e upload de arquivos
- Implementa a extração de áudio de vídeos

#### `logging_config.py`

Configura o sistema de logging:

- Define formatos de log para console e arquivo
- Configura níveis de log
- Implementa formatação colorida para o console

#### `retry_utils.py`

Implementa mecanismos de retry para operações do Telegram:

- Decorador `@retry_telegram_operation` para retry automático
- Lida com erros temporários e FloodWait do Telegram
- Implementa backoff exponencial

### 2. Módulo de Tarefas

#### `tasks/publish_pipeline.py`

Implementa o pipeline de publicação (Zimatise):

- Orquestra as etapas do workflow: Zip, Report, Re-encode, Join, Timestamp
- Gerencia o estado de cada etapa no banco de dados
- Implementa a lógica de upload para o Telegram

#### `zimatise_one.py`

Implementação original do workflow Zimatise, agora refatorada para o pipeline modular.

## Banco de Dados

O Clonechat utiliza um banco de dados SQLite (`data/clonechat.db`) com as seguintes tabelas:

### Tabela `SyncTasks`

Armazena informações sobre tarefas de clonagem:

- `origin_chat_id`: ID do canal de origem
- `origin_chat_title`: Nome do canal de origem
- `destination_chat_id`: ID do canal de destino
- `cloning_strategy`: Estratégia usada (forward/download_upload)
- `last_synced_message_id`: ID da última mensagem sincronizada

### Tabela `DownloadTasks`

Armazena informações sobre tarefas de download de vídeos:

- `origin_chat_id`: ID do canal de origem
- `origin_chat_title`: Nome do canal de origem
- `last_downloaded_message_id`: ID da última mensagem baixada
- `total_videos`: Total de vídeos no canal
- `downloaded_videos`: Número de vídeos já baixados
- `created_at`: Data de criação da tarefa
- `updated_at`: Data da última atualização

### Tabela `PublishTasks`

Armazena informações sobre tarefas de publicação (pipeline Zimatise):

- `source_folder_path`: Caminho da pasta fonte (chave primária)
- `project_name`: Nome do projeto
- `destination_chat_id`: ID do chat de destino
- `current_step`: Etapa atual do pipeline
- `status`: Status da tarefa (pending, running, completed, failed)
- `is_started`: Flag se a tarefa foi iniciada
- `is_zipped`: Flag se a compactação foi concluída
- `is_reported`: Flag se os relatórios foram gerados
- `is_reencode_auth`: Flag se a autorização de recodificação foi obtida
- `is_reencoded`: Flag se a recodificação foi concluída
- `is_joined`: Flag se a junção foi concluída
- `is_timestamped`: Flag se os timestamps foram adicionados
- `is_upload_auth`: Flag se a autorização de upload foi obtida
- `is_published`: Flag se a publicação foi concluída
- `last_uploaded_file`: Último arquivo enviado
- `created_at`: Data de criação da tarefa
- `updated_at`: Data da última atualização

## Bibliotecas e Dependências

### Principais Bibliotecas

#### Pyrogram

Biblioteca cliente para a API do Telegram:

- Gerencia a autenticação e sessão do Telegram
- Fornece métodos para interagir com chats, mensagens e mídias
- Implementa handlers para eventos do Telegram

#### Typer

Biblioteca para criação de interfaces de linha de comando:

- Define comandos, argumentos e opções
- Fornece help automático e validação de argumentos
- Implementa formatação colorida para o terminal

#### SQLite3

Banco de dados embutido para persistência de dados:

- Armazena o estado das tarefas
- Rastreia o progresso de clonagem, download e publicação
- Permite retomar operações interrompidas

#### FFmpeg

Ferramenta externa para processamento de mídia:

- Extrai áudio de vídeos
- Recodifica vídeos para formatos compatíveis
- Junta múltiplos vídeos em arquivos maiores

#### Python-dotenv

Biblioteca para gerenciamento de variáveis de ambiente:

- Carrega configurações do arquivo `.env`
- Gerencia credenciais e configurações sensíveis

### Dependências Adicionais

#### Para o Pipeline Zimatise

- `vidtool`: Ferramenta para processamento de vídeos
- `zipind`: Ferramenta para compactação de arquivos
- `pandas`: Biblioteca para manipulação de dados tabulares (relatórios)
- `openpyxl`: Biblioteca para manipulação de arquivos Excel

## Arquitetura e Padrões

### Arquitetura Orientada a Comandos

Cada comando da CLI é um fluxo de trabalho independente que orquestra suas próprias dependências.

### Pipeline de Dados (para `publish`)

A funcionalidade Zimatise é modelada como um pipeline de dados sequencial:

1. **Zip**: Compacta arquivos não-mídia
2. **Report**: Gera relatório de vídeos
3. **Re-encode**: Recodifica vídeos
4. **Join**: Junta múltiplos vídeos
5. **Timestamp**: Gera metadados de timestamp
6. **Upload**: Envia arquivos para o Telegram

### Camada de Acesso a Dados (DAL)

O módulo `database.py` serve como uma camada de abstração, isolando a lógica SQL do resto da aplicação.

### Princípio da Responsabilidade Única (SRP)

- `engine.py`: Responsável apenas pelo fluxo de clonagem de chat
- `tasks/publish_pipeline.py`: Responsável apenas pelo fluxo de publicação
- `database.py`: Responsável apenas pela interação com o banco de dados
- `processor.py`: Responsável apenas pela lógica de processamento de mensagens

## Fluxos de Trabalho

### Fluxo de Clonagem

1. O usuário executa o comando `sync` com parâmetros apropriados
2. O sistema verifica se a tarefa já existe no banco de dados
3. Se existir, retoma de onde parou; se não, cria uma nova tarefa
4. Detecta automaticamente a estratégia de clonagem (forward ou download_upload)
5. Processa as mensagens do canal de origem
6. Atualiza o progresso no banco de dados após cada mensagem
7. Salva o link do canal clonado em `links_canais.txt`
8. Opcionalmente publica o link em um grupo/canal especificado

### Fluxo de Download

1. O usuário executa o comando `download` com parâmetros apropriados
2. O sistema verifica se a tarefa já existe no banco de dados
3. Se existir, retoma de onde parou; se não, cria uma nova tarefa
4. Baixa os vídeos do canal de origem
5. Extrai áudio de cada vídeo
6. Atualiza o progresso no banco de dados após cada vídeo

### Fluxo de Publicação (Zimatise)

1. O usuário executa o comando `publish` com o caminho da pasta
2. O sistema verifica se a tarefa já existe no banco de dados
3. Se existir, retoma da última etapa concluída; se não, cria uma nova tarefa
4. Executa sequencialmente as etapas do pipeline:
   - Compacta arquivos não-mídia
   - Gera relatório de vídeos
   - Recodifica vídeos conforme especificado
   - Junta múltiplos vídeos
   - Gera metadados de timestamp
5. Cria um canal de destino para a publicação
6. Faz upload dos arquivos processados para o canal
7. Publica e fixa uma mensagem de sumário
8. Opcionalmente publica o link do canal em um grupo/canal especificado

## Boas Práticas Implementadas

### Gerenciamento de Segredos

- Nenhuma credencial no código
- Todas as chaves e tokens são carregados de um arquivo `.env`

### Logging Robusto

- O módulo `logging` é a única fonte para saídas de status, progresso e erro
- Logs detalhados com formatação colorida
- Saída para console e arquivo

### Tratamento de Erros e Retentativas

- Uso do decorador `@retry_telegram_operation` para todas as chamadas de API
- Backoff exponencial para evitar FloodWait
- Tratamento adequado de exceções

### Código Limpo e Desacoplado

- Separação clara entre as tarefas de `clone` e `publish`
- Baixo acoplamento entre componentes
- Reutilização de código onde aplicável

## Configuração e Ambiente

### Variáveis de Ambiente (.env)

```ini
TELEGRAM_API_ID=SeuApiIdAqui
TELEGRAM_API_HASH=SeuApiHashAqui
CLONER_DELAY_SECONDS=2
CLONER_DOWNLOAD_PATH=./data/downloads/
```

### Requisitos de Sistema

- **Python 3.9+**
- **FFmpeg** instalado e disponível no PATH
- **Build Tools do Visual Studio** para a biblioteca `tgcrypto`
- **Credenciais do Telegram** (API ID e API Hash)

## Considerações de Segurança

- **Nunca compartilhe** suas credenciais publicamente
- **Não commite** o arquivo `.env` no repositório
- **Use números de telefone ativos** para evitar problemas de verificação
- **Respeite os Termos de Serviço** da API do Telegram
- **Evite spam e flooding** para não ser banido

## Extensibilidade

O projeto foi projetado para ser facilmente extensível:

- Novos comandos podem ser adicionados à CLI
- Novas etapas podem ser adicionadas ao pipeline de publicação
- Novos tipos de mídia podem ser suportados no processador

## Conclusão

O Clonechat é uma ferramenta robusta para automação do Telegram, com arquitetura modular e extensível. A separação clara entre os componentes e a persistência de estado permitem que operações sejam interrompidas e retomadas, tornando a ferramenta resiliente e confiável.

A documentação acima fornece uma visão detalhada da estrutura, componentes e fluxos de trabalho do projeto, facilitando a manutenção e extensão futura.