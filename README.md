# Clonechat

Ferramenta avançada para clonar chats do Telegram com arquitetura moderna e recursos avançados.

## 🚀 Características

- **Clonagem Automática**: Criação automática de canais de destino
- **Detecção Inteligente**: Estratégia automática (forward ou download-upload)
- **Extração de Áudio Opcional**: Extraia áudio de vídeos com a flag `--extract-audio` ao usar a estratégia `download-upload`.
- **Forçar Estratégia**: Opção `--force-download` para forçar a estratégia `download-upload`.
- **Salvamento de Links**: Arquivo `links_canais.txt` com links dos canais clonados
- **Processamento de Mídia**: Suporte completo a todos os tipos de mensagem
- **Logging Avançado**: Sistema de logs estruturado com saída para console e arquivo
- **Retry Inteligente**: Mecanismo de retry com backoff exponencial
- **Processamento em Lote**: Suporte a múltiplos chats via arquivo
- **Resumo de Tarefas**: Continua de onde parou automaticamente
- **Arquitetura Async**: Performance otimizada com asyncio
- **Download de Vídeos**: Comando dedicado para baixar vídeos com extração de áudio
- **Sistema de Resumo**: Banco de dados para rastrear progresso de downloads
- **Identificação Flexível**: Aceita IDs, usernames e links do Telegram
- **Controle de Progresso**: Opções para limitar downloads e forçar restart

## 📋 Pré-requisitos

- **Python 3.9+**
- **FFmpeg** instalado e disponível no PATH do Windows
    - Baixe em: https://ffmpeg.org/download.html
    - Adicione o executável à variável de ambiente PATH
- **Build Tools do Visual Studio** para instalar a biblioteca `tgcrypto`
    - Instale via: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- **Credenciais do Telegram** (API ID e API Hash)
    - Obtenha em: https://my.telegram.org/apps

## 🔑 Como Obter as Credenciais do Telegram

### 1. API ID e API Hash

Para usar a API do Telegram, você precisa criar uma aplicação e obter suas credenciais:

#### Passo 1: Acesse o Telegram Core
1. Abra seu navegador e vá para: https://my.telegram.org
2. Faça login com seu número de telefone do Telegram
3. Clique em "API development tools"

#### Passo 2: Crie uma Nova Aplicação
1. Preencha o formulário com as seguintes informações:
   - **App title**: Nome da sua aplicação (ex: "Clonechat")
   - **Short name**: Nome curto (ex: "clonechat")
   - **Platform**: Selecione "Desktop"
   - **Description**: Descrição da aplicação (ex: "Ferramenta para clonar chats do Telegram")

#### Passo 3: Obtenha as Credenciais
Após submeter o formulário, você receberá:
- **api_id**: Um número inteiro (ex: 12345678)
- **api_hash**: Uma string hexadecimal (ex: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")

⚠️ **Importante**: Mantenha essas credenciais seguras e nunca as compartilhe publicamente.

### 2. Token do Bot (Opcional)

Se você planeja usar funcionalidades que requerem um bot, siga estes passos:

#### Passo 1: Acesse o BotFather
1. Abra o aplicativo Telegram
2. Na barra de pesquisa, digite `@BotFather`
3. Selecione o bot oficial (tem um selo de verificação azul)
4. Clique em "Iniciar"

#### Passo 2: Crie um Novo Bot
1. Digite o comando `/newbot` ou clique no comando na lista
2. O BotFather solicitará um nome para seu bot (visível para usuários)
3. Escolha um nome de usuário (username) que deve:
   - Ser único
   - Terminar com "bot" (ex: "meu_bot", "teste123_bot")

#### Passo 3: Receba o Token
Após a criação, o BotFather fornecerá:
- Link para acessar seu bot: `t.me/seu_bot_username`
- Token único no formato: `123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

#### Configurações Adicionais do Bot (Opcional)
- **Desabilitar Grupos**: Para bots que funcionam apenas em conversas privadas
  - Digite `/mybots`
  - Selecione seu bot → Bot Settings → Allow Groups → Turn groups off
- **Definir Descrição**: Use `/setdescription` para adicionar uma descrição

### 3. Configuração das Credenciais

Após obter suas credenciais, configure-as no arquivo `.env`:

```ini
# Credenciais obrigatórias
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# Credenciais opcionais (se usar funcionalidades de bot)
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Configurações da aplicação
CLONER_DELAY_SECONDS=2
CLONER_DOWNLOAD_PATH=./data/downloads/
```

### ⚠️ Observações de Segurança

- **Nunca compartilhe** suas credenciais publicamente
- **Não commite** o arquivo `.env` no repositório
- **Use números de telefone ativos** para evitar problemas de verificação
- **Respeite os Termos de Serviço** da API do Telegram
- **Evite spam e flooding** para não ser banido

### 🔧 Solução de Problemas com Credenciais

#### Erro: "API_ID is required"
- Verifique se o arquivo `.env` existe e está configurado corretamente
- Confirme se as credenciais foram copiadas sem espaços extras

#### Erro: "Invalid API ID/Hash"
- Verifique se as credenciais estão corretas
- Confirme se você está usando o número de telefone correto

#### Erro: "Phone number banned"
- Se sua conta foi banida, entre em contato com recover@telegram.org
- Explique seu caso de uso e peça para desbanir sua conta

## 🛠️ Instalação

### Pré-requisitos
- **Python 3.9+** instalado
- **Poetry** instalado (gerenciador de dependências)

### 1. Instalar o Poetry (se não tiver)
```bash
# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Ou via pip
pip install poetry
```

### 2. Clone o repositório
```bash
git clone <repository-url>
cd chatclone
```

### 3. Instalar dependências com Poetry
```bash
# Instalar todas as dependências
poetry install

# Ou ativar o ambiente virtual e instalar
poetry shell
poetry install
```

### 4. Configurar credenciais
```bash
# Copiar arquivo de exemplo
copy .env.example .env

# Editar o arquivo .env com suas credenciais
# TELEGRAM_API_ID=SeuApiIdAqui
# TELEGRAM_API_HASH=SeuApiHashAqui
```

### 5. Executar o projeto
```bash
# Usando Poetry
poetry run python main.py --help

# Ou ativando o ambiente virtual
poetry shell
python main.py --help
```

### Comandos úteis do Poetry
```bash
# Ver dependências instaladas
poetry show

# Adicionar nova dependência
poetry add nome-do-pacote

# Remover dependência
poetry remove nome-do-pacote

# Atualizar dependências
poetry update

# Ver informações do projeto
poetry version
```

### Alternativa: Usando venv (Ambiente Virtual Python)

Se preferir usar o ambiente virtual padrão do Python ao invés do Poetry:

#### 1. Criar ambiente virtual
```bash
# Windows
python -m venv venv

# Ativar o ambiente virtual
venv\Scripts\activate
```

#### 2. Instalar dependências
```bash
# Com o ambiente virtual ativado
pip install -r requirements.txt
```

#### 3. Executar o projeto
```bash
# Com o ambiente virtual ativado
python main.py --help
```

#### 4. Desativar ambiente virtual
```bash
deactivate
```

### Comparação: Poetry vs venv

| Aspecto | Poetry | venv |
|---------|--------|------|
| **Gerenciamento** | Automático | Manual |
| **Dependências** | `pyproject.toml` | `requirements.txt` |
| **Lock file** | `poetry.lock` | Nenhum |
| **Comando** | `poetry run python main.py` | `python main.py` |
| **Instalação** | `poetry install` | `pip install -r requirements.txt` |
| **Isolamento** | ✅ | ✅ |
| **Versões** | Fixas | Flexíveis |

**Recomendação**: Use **Poetry** para melhor controle de versões e isolamento.

## 📖 Uso

### Clonagem Individual (Estratégia Automática)
```bash
poetry run python main.py sync --origin <ID_DO_CANAL>
```
- Detecta automaticamente se pode usar `forward` ou `download_upload`
- **Não extrai áudio** se usar estratégia `forward`
- **Não sai** do canal de origem por padrão

### Clonagem com Extração de Áudio (Requer Estratégia Download-Upload)
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --extract-audio
```
- **Extrai áudio** de vídeos se a estratégia `download-upload` for usada.
- Arquivos MP3 são salvos na pasta do canal
- Se o canal não permitir encaminhamento, a estratégia `download-upload` será usada automaticamente. Se permitir, use `--force-download` para forçar a estratégia e permitir a extração.

### Clonagem Forçando Estratégia Download-Upload
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --force-download
```
- **Sempre usa** a estratégia `download-upload`, mesmo que o encaminhamento seja permitido.
- **Não extrai áudio** por padrão. Use `--extract-audio` para isso.

### Clonagem para Canal Existente
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --dest <ID_CANAL_DESTINO>
```
- Usa um canal de destino existente em vez de criar um novo
- Útil para continuar clonando em um canal já existente

### Clonagem e Sair do Canal de Origem
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --leave-origin
```
- Sai automaticamente do canal de origem após a clonagem
- Por padrão, permanece no canal de origem

### Clonagem e Publicar Links
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --publish-to <ID_GRUPO/CANAL>
```
- Publica automaticamente os links dos canais clonados em um grupo/canal
- Útil para manter uma lista atualizada dos canais clonados
- O link é publicado após cada clonagem bem-sucedida

### Clonagem e Publicar em Tópico Específico
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --publish-to <ID_GRUPO> --topic <ID_TOPICO>
```
- Publica os links em um tópico específico de um grupo
- Requer que o grupo tenha tópicos habilitados
- Útil para organizar links por categoria

### Combinações de Opções
```bash
# Clonagem completa: forçar download, extrair áudio, usar canal existente, sair do origem e publicar links
poetry run python main.py sync --origin <ID_DO_CANAL> --force-download --extract-audio --dest <ID_DESTINO> --leave-origin --publish-to <ID_GRUPO>

# Clonagem simples para canal existente e publicar links
poetry run python main.py sync --origin <ID_DO_CANAL> --dest <ID_DESTINO> --publish-to <ID_GRUPO>
```

### Clonagem em Lote
```bash
poetry run python main.py sync --batch --source arquivo_com_ids.txt
```

### Clonagem em Lote com Extração de Áudio
```bash
poetry run python main.py sync --batch --source arquivo_com_ids.txt --extract-audio
```

### Modo Restart (Força Nova Clonagem)
```bash
poetry run python main.py sync --origin <ID_DO_CANAL> --restart
```

### Verificar Versão
```bash
poetry run python main.py version
```

### Inicializar Banco de Dados
```bash
poetry run python main.py init-database
```
- Inicializa ou atualiza o banco de dados
- Cria as tabelas necessárias (SyncTasks, DownloadTasks e PublishTasks)
- Útil após atualizações que adicionam novas tabelas

### Listar Chats Disponíveis
```bash
poetry run python main.py list-chats
```
- Lista todos os chats, grupos e canais que o usuário tem acesso
- Mostra ID, nome e tipo de cada chat
- Útil para verificar IDs corretos dos canais

### Testar Resolução de Chat
```bash
poetry run python main.py test-resolve --id <ID_DO_CANAL>
```
- Testa se um ID, username ou link de chat pode ser resolvido
- Verifica se o usuário tem acesso ao chat
- Útil para diagnosticar problemas de acesso

### Download de Vídeos com Extração de Áudio
```bash
poetry run python main.py download --origin <ID_DO_CANAL>
```
- Baixa todos os vídeos de um canal
- Extrai automaticamente o áudio de cada vídeo em MP3
- Mantém tanto o vídeo quanto o áudio
- Salva os arquivos organizados por data e ID da mensagem
- **Resume automaticamente** de onde parou se interrompido

### Download com Limite de Vídeos
```bash
poetry run python main.py download --origin <ID_DO_CANAL> --limit 10
```
- Baixa apenas os 10 vídeos mais recentes
- Útil para testar ou baixar apenas alguns vídeos

### Download para Diretório Específico
```bash
poetry run python main.py download --origin <ID_DO_CANAL> --output ./meus_videos/
```
- Salva os arquivos em um diretório específico
- Por padrão, salva em `./downloads/Nome_do_Canal/`

### Download com Restart (Força Novo Download)
```bash
poetry run python main.py download --origin <ID_DO_CANAL> --restart
```
- Força um novo download do zero
- Apaga dados anteriores de progresso
- Útil quando quer recomeçar completamente

### Publicação de Pastas Locais (Pipeline Zimatise)
```bash
poetry run python main.py publish --folder <CAMINHO_PASTA>
```
- Publica uma pasta local no Telegram usando o pipeline Zimatise
- Processa automaticamente através de várias etapas:
  1. **Compactação** de arquivos
  2. **Geração** de relatórios
  3. **Recodificação** de vídeos
  4. **Junção** de arquivos
  5. **Adição** de timestamps
  6. **Upload** para Telegram
- **Resume automaticamente** de onde parou se interrompido
- Útil para backup e compartilhamento de projetos

### Publicação com Restart (Força Nova Publicação)
```bash
poetry run python main.py publish --folder <CAMINHO_PASTA> --restart
```
- Força uma nova publicação do zero
- Apaga dados anteriores de progresso
- Útil quando quer recomeçar completamente

### Exemplos de Publicação
```bash
# Publicar pasta de projeto
poetry run python main.py publish --folder C:/meus_projetos/curso_python

# Publicar pasta com restart
poetry run python main.py publish --folder C:/meus_projetos/curso_python --restart

# Publicar pasta com caminho relativo
poetry run python main.py publish --folder ./projetos/meu_projeto
```

### Comandos de Diagnóstico

#### `list-chats`
Lista todos os chats acessíveis pela sua conta:
```bash
poetry run python main.py list-chats
```

#### `list-topics`
Lista todos os tópicos de um grupo com tópicos habilitados:
```bash
poetry run python main.py list-topics --id <ID_GRUPO>
```
- Mostra o ID e o nome de cada tópico
- Útil para descobrir o ID correto para usar com `--topic`
- Só funciona em grupos com tópicos habilitados

#### `test-resolve`
Testa a resolução de um identificador de chat:
```bash
poetry run python main.py test-resolve --id <ID_USERNAME_LINK>
```

## 📁 Estrutura do Projeto

```
chatclone/
├── data/
│   ├── clonechat.db         # Banco de dados SQLite
│   │   ├── SyncTasks        # Tarefas de clonagem
│   │   └── DownloadTasks    # Tarefas de download
│   ├── downloads/           # Arquivos temporários e áudio extraído
│   │   └── -100123456789 - Nome do Canal/
│   │       ├── 2-video.mp4          # Vídeo original (apagado após upload)
│   │       ├── 2-video.mp3          # Áudio extraído (PRESERVADO)
│   │       └── ...
│   └── app.log             # Logs da aplicação
├── links_canais.txt        # Links dos canais clonados
├── config.py               # Gerenciamento de configuração
├── database.py             # Camada de acesso a dados
├── engine.py               # Motor principal de clonagem
├── processor.py            # Processamento de mensagens
├── cli.py                  # Interface de linha de comando
├── logging_config.py       # Configuração de logging
├── retry_utils.py          # Utilitários de retry
├── main.py                 # Ponto de entrada
└── pyproject.toml          # Configuração do projeto
```

## 🔧 Configuração

### Variáveis de Ambiente (.env)
```ini
TELEGRAM_API_ID=SeuApiIdAqui
TELEGRAM_API_HASH=SeuApiHashAqui
CLONER_DELAY_SECONDS=2
CLONER_DOWNLOAD_PATH=./data/downloads/
```

### Arquivo de Lote (para processamento em massa)
Crie um arquivo de texto com IDs de chat, um por linha:
```
-123456789
-987654321
-555666777
```

## 📊 Funcionalidades

### Estratégias de Clonagem
- **Forward**: Encaminhamento direto (mais rápido, sem extração de áudio)
- **Download-Upload**: Download, processamento e upload (extrai áudio de vídeos)

### Tipos de Mídia Suportados
- Texto, Fotos, Vídeos, Documentos
- Áudios, Voice Messages, Stickers
- Animações, Video Notes, Polls

### Recursos Avançados
- **Extração de Áudio**: Com a flag `--extract-audio`, vídeos são processados para extrair áudio em MP3 quando a estratégia `download-upload` é usada.
- **Força Download**: Opção `--force-download` para sempre usar a estratégia `download-upload`.
- **Canal de Destino Existente**: Opção `--dest` para usar canal existente
- **Controle de Saída**: Opção `--leave-origin` para sair do canal de origem
- **Salvamento de Links**: Links dos canais clonados salvos em `links_canais.txt`
- **Logging Estruturado**: Logs detalhados com formatação colorida
- **Retry Inteligente**: Tratamento automático de erros do Telegram
- **Progresso Persistente**: Continua de onde parou em execuções subsequentes
- **Sistema de Resumo**: Tarefas de clonagem e download são salvas no banco de dados
- **Download com Resumo**: Downloads podem ser interrompidos e retomados automaticamente
- **Identificação Flexível**: Aceita IDs, usernames e links do Telegram

### Arquivo de Links dos Canais
Após cada clonagem, o arquivo `links_canais.txt` é atualizado com:
```
Nome do Canal Original
https://t.me/c/1234567890/1
Nome do Canal Original 2
https://t.me/c/9876543210/1
```

### Publicação Automática de Links
O Clonechat pode publicar automaticamente os links dos canais clonados em grupos ou canais:

#### Formato da Mensagem Publicada
A mensagem publicada terá um formato simples e direto:
```
Nome do Canal Original
https://t.me/c/1234567890/1
```

#### Benefícios da Publicação Automática
- **Organização**: Mantém uma lista atualizada dos canais clonados
- **Colaboração**: Compartilha links com equipe/membros
- **Rastreamento**: Facilita o acompanhamento de clonagens
- **Categorização**: Use tópicos para organizar por tipo de conteúdo

#### Configuração de Tópicos
Para grupos com tópicos habilitados, você pode especificar um tópico específico:
- Use `--topic <ID_TOPICO>` para publicar em um tópico específico
- Use `poetry run python main.py list-topics --id <ID_GRUPO>` para descobrir os IDs dos tópicos
- Útil para organizar links por categoria (ex: "Canais de Tecnologia", "Canais de Marketing")
- O ID do tópico pode ser obtido através do comando `list-topics` ou da API do Telegram

### Sistema de Resumo e Progresso
O Clonechat mantém o progresso de todas as operações no banco de dados SQLite:

#### Tabela SyncTasks (Clonagem)
- `origin_chat_id`: ID do canal de origem
- `origin_chat_title`: Nome do canal de origem
- `destination_chat_id`: ID do canal de destino
- `cloning_strategy`: Estratégia usada (forward/download_upload)
- `last_synced_message_id`: ID da última mensagem sincronizada

#### Tabela DownloadTasks (Download de Vídeos)
- `origin_chat_id`: ID do canal de origem
- `origin_chat_title`: Nome do canal de origem
- `last_downloaded_message_id`: ID da última mensagem baixada
- `total_videos`: Total de vídeos no canal
- `downloaded_videos`: Número de vídeos já baixados
- `created_at`: Data de criação da tarefa
- `updated_at`: Data da última atualização

#### Tabela PublishTasks (Publicação)
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

#### Benefícios do Sistema de Resumo
- **Interrupção Segura**: Pode parar e retomar operações a qualquer momento
- **Eficiência**: Não reprocessa conteúdo já baixado/clonado
- **Transparência**: Mostra progresso detalhado das operações
- **Controle**: Opção `--restart` para forçar novo processamento

## 🐛 Solução de Problemas

### FFmpeg não encontrado
```
❌ FFmpeg not found in PATH
```
**Solução**: Instale o FFmpeg e adicione ao PATH do Windows.

### Erro de Build Tools
```
error: Microsoft Visual C++ 14.0 or greater is required
```
**Solução**: Instale o Build Tools do Visual Studio.

### Credenciais inválidas
```
TELEGRAM_API_ID is required
```
**Solução**: Configure corretamente o arquivo `.env`.

### Erro de tabela não encontrada
```
no such table: DownloadTasks
```
**Solução**: Execute `poetry run python main.py init-database` para criar as tabelas necessárias.

### Erro de acesso a chat
```
Cannot resolve chat identifier
```
**Solução**: 
- Verifique se você é membro do canal/grupo
- Use `poetry run python main.py list-chats` para ver os chats disponíveis
- Use `poetry run python main.py test-resolve --id <ID>` para testar acesso específico

### Áudio não sendo extraído
```
FFmpeg not found in PATH
```
**Solução**: Instale o FFmpeg e adicione ao PATH do Windows.

## 📝 Logs

Os logs são salvos em `data/app.log` e também exibidos no console:
- **INFO**: Operações normais
- **WARNING**: Avisos e situações não críticas
- **ERROR**: Erros que precisam de atenção

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para detalhes.

## ⚠️ Observações Importantes

- O FFmpeg **deve** estar instalado e disponível no PATH antes de rodar o projeto
- O Build Tools do Visual Studio é necessário para instalar a dependência nativa `tgcrypto`
- O arquivo `.env**não** deve ser versionado
- Use o modo `--restart` com cuidado, pois apaga dados anteriores
- O sistema cria automaticamente canais de destino (a menos que `--dest` seja especificado)
- Use a combinação `--force-download` e `--extract-audio` para garantir a extração de áudio de todos os vídeos.
- Os arquivos MP3 extraídos são preservados na pasta do canal
- Por padrão, o sistema **não sai** do canal de origem (use `--leave-origin` se necessário)
- Ao usar `--dest`, certifique-se de ter permissões de escrita no canal de destino 

## 💡 Exemplos Práticos

### Fluxo Completo de Clonagem
```bash
# 1. Verificar acesso ao canal
poetry run python main.py test-resolve --id -1002859374479

# 2. Clonar com extração de áudio (forçando a estratégia de download) e publicar links
poetry run python main.py sync --origin -1002859374479 --force-download --extract-audio --publish-to -1001234567890

# 3. Verificar links salvos
cat links_canais.txt
```

### Fluxo Completo de Clonagem com Tópicos
```bash
# 1. Verificar acesso ao canal
poetry run python main.py test-resolve --id -1002859374479

# 2. Listar tópicos do grupo onde publicar
poetry run python main.py list-topics --id -1001234567890

# 3. Clonar e publicar em tópico específico
poetry run python main.py sync --origin -1002859374479 --publish-to -1001234567890 --topic 123

# 4. Verificar links salvos
cat links_canais.txt
```

### Fluxo de Download de Vídeos
```bash
# 1. Listar canais disponíveis
poetry run python main.py list-chats

# 2. Baixar vídeos com limite
poetry run python main.py download --origin -1002859374479 --limit 5

# 3. Se interrompido, retomar automaticamente
poetry run python main.py download --origin -1002859374479

# 4. Para forçar novo download
poetry run python main.py download --origin -1002859374479 --restart
```

### Fluxo de Publicação de Pastas
```bash
# 1. Publicar pasta de projeto
poetry run python main.py publish --folder C:/meus_projetos/curso_python

# 2. Se interrompido, retomar automaticamente
poetry run python main.py publish --folder C:/meus_projetos/curso_python

# 3. Para forçar nova publicação
poetry run python main.py publish --folder C:/meus_projetos/curso_python --restart

# 4. Publicar pasta com caminho relativo
poetry run python main.py publish --folder ./projetos/meu_projeto
```

### Diagnóstico de Problemas
```bash
# Verificar versão
poetry run python main.py version

# Inicializar banco de dados
poetry run python main.py init-database

# Testar acesso específico
poetry run python main.py test-resolve --id @canal_username

# Listar todos os chats
poetry run python main.py list-chats

# Listar tópicos de um grupo
poetry run python main.py list-topics --id -1001234567890
```

### Uso Avançado
```bash
# Clonar para canal existente
poetry run python main.py sync --origin -1002859374479 --dest -1002749622339

# Clonar e sair do canal origem
poetry run python main.py sync --origin -1002859374479 --leave-origin

# Clonar e publicar links em grupo
poetry run python main.py sync --origin -1002859374479 --publish-to -1001234567890

# Clonar e publicar em tópico específico
poetry run python main.py sync --origin -1002859374479 --publish-to -1001234567890 --topic 123

# Download para diretório específico
poetry run python main.py download --origin -1002859374479 --output ./meus_videos/

# Processamento em lote
poetry run python main.py sync --batch --source canais.txt

# Publicação de pastas locais
poetry run python main.py publish --folder C:/meus_projetos/curso_python

# Publicação com restart
poetry run python main.py publish --folder C:/meus_projetos/curso_python --restart
```