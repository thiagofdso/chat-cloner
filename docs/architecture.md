# Arquitetura do Projeto Clonechat

## Visão Geral

O Clonechat é uma ferramenta de linha de comando (CLI) construída em Python para automatizar tarefas de clonagem e publicação de conteúdo no Telegram. Ele utiliza a biblioteca `Pyrogram` para interagir com a API do Telegram e `Typer` para criar a interface de linha de comando.

A arquitetura é modular, separando a lógica de CLI, o motor de clonagem, o acesso ao banco de dados, o processamento de mídia e as configurações em diferentes módulos.

## Estrutura de Arquivos

```
C:\whatsweb\chatclone/
├── clonechat/              # Módulo principal da aplicação
│   ├── __init__.py
│   ├── cli.py              # Interface de linha de comando (Typer)
│   ├── config.py           # Carregamento e validação de configurações
│   ├── database.py         # Funções de acesso ao banco de dados (SQLite)
│   ├── engine.py           # Motor principal para clonagem de chats
│   ├── logging_config.py   # Configuração de logs
│   ├── processor.py        # Lógica de processamento de mensagens (forward, download/upload)
│   ├── retry_utils.py      # Utilitários de retentativa para operações de API
│   ├── zimatise_one.py     # (Parece ser um resquício ou script de teste)
│   └── tasks/
│       ├── __init__.py
│       └── publish_pipeline.py # Lógica do pipeline de publicação de pastas
├── data/                   # Dados da aplicação (ignorado pelo git)
│   ├── clonechat.db        # Banco de dados SQLite
│   ├── downloads/          # Arquivos baixados durante o processo
│   └── project_workspace/  # Arquivos de trabalho para o pipeline de publicação
├── docs/                   # Documentação do projeto
│   ├── architecture.md     # Este arquivo
│   └── requirements.md     # Requisitos funcionais
├── .env.example            # Exemplo de arquivo de configuração de ambiente
├── .gitignore              # Arquivos e pastas ignorados pelo Git
├── main.py                 # Ponto de entrada da aplicação
├── media_processor.py      # Script para processamento de mídia (extração de áudio)
├── pyproject.toml          # Arquivo de configuração do projeto (Poetry)
├── README.md               # Documentação principal do projeto
├── requirements.txt        # Dependências do projeto
└── reset_timestamp.py      # Script utilitário para resetar status de tarefas
```

### Descrição dos Componentes

- **`main.py`**: O ponto de entrada que inicializa e executa a aplicação CLI definida em `clonechat/cli.py`.

- **`clonechat/cli.py`**: Define todos os comandos disponíveis na CLI (`sync`, `download`, `publish`, `list-chats`, etc.) usando `Typer`. Ele orquestra as operações, chamando as funções apropriadas do motor (`engine.py`) e de outros módulos.

- **`clonechat/engine.py`**: Contém a classe `ClonerEngine`, que é o cérebro por trás da funcionalidade de `sync`. Ele gerencia a lógica de clonagem, determina a estratégia (encaminhamento direto ou download/upload), cria canais de destino e lida com o estado da tarefa.

- **`clonechat/processor.py`**: Fornece as funções de baixo nível para processar mensagens individuais. Contém a implementação das estratégias `forward_message` e `download_process_upload`, além de funções para manipular tipos específicos de mídia.

- **`clonechat/database.py`**: Abstrai todas as interações com o banco de dados SQLite. Define o esquema das tabelas (`SyncTasks`, `DownloadTasks`, `PublishTasks`) e fornece funções CRUD para gerenciar o estado das tarefas de clonagem, download e publicação.

- **`clonechat/config.py`**: Responsável por carregar as configurações da aplicação a partir de um arquivo `.env` ou de variáveis de ambiente. Utiliza um dataclass `Config` para manter as configurações de forma organizada.

- **`clonechat/tasks/publish_pipeline.py`**: Implementa a lógica complexa do comando `publish`. A classe `PublishPipeline` orquestra uma série de etapas (compactação, geração de relatórios, re-codificação, etc.) para preparar e enviar uma pasta local para o Telegram.

- **`clonechat/logging_config.py`**: Centraliza a configuração do sistema de logs para toda a aplicação, permitindo saídas consistentes no console e em arquivos.

- **`media_processor.py`**: Um script que parece ter uma funcionalidade similar à extração de áudio já presente no `processor.py`. Pode ser um resquício de uma refatoração ou um script de teste.

- **`reset_timestamp.py`**: Um script de utilidade para resetar o estado de uma tarefa de publicação no banco de dados, forçando a re-execução de certas etapas do pipeline.

## Fluxo de Dados

1.  O usuário executa um comando via `main.py` (ex: `python main.py sync ...`).
2.  `cli.py` parseia os argumentos e chama a função assíncrona correspondente (ex: `run_sync_async`).
3.  `config.py` é usado para carregar as credenciais e configurações.
4.  O `ClonerEngine` (`engine.py`) é inicializado.
5.  O motor consulta o `database.py` para verificar se existe uma tarefa pendente.
6.  Com base na tarefa e nos argumentos, o motor itera sobre as mensagens do chat de origem.
7.  Para cada mensagem, o `processor.py` é chamado para aplicar a estratégia de clonagem (encaminhar ou baixar/enviar).
8.  O progresso é continuamente salvo no banco de dados via `database.py`.
9.  Logs são gerados em todas as etapas através do `logging_config.py`.
