# Clonechat

Ferramenta avançada para clonar chats do Telegram com arquitetura moderna e recursos avançados.

## 🚀 Características

- **Clonagem Automática**: Criação automática de canais de destino
- **Detecção Inteligente**: Estratégia automática (forward ou download-upload)
- **Extração de Áudio**: Extração automática de áudio de vídeos via FFmpeg
- **Força Download**: Opção para forçar estratégia download-upload e extrair áudio
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

## 🛠️ Instalação

1. **Clone o repositório:**
```bash
git clone <repository-url>
cd chatclone
```

2. **Instale as dependências:**
```bash
poetry install
```

3. **Configure as credenciais:**
```bash
copy .env.example .env
# Edite o arquivo .env e insira seu TELEGRAM_API_ID e TELEGRAM_API_HASH
```

## 📖 Uso

### Clonagem Individual (Estratégia Automática)
```bash
python main.py sync --origin <ID_DO_CANAL>
```
- Detecta automaticamente se pode usar `forward` ou `download_upload`
- **Não extrai áudio** se usar estratégia `forward`
- **Não sai** do canal de origem por padrão

### Clonagem com Extração de Áudio Forçada
```bash
python main.py sync --origin <ID_DO_CANAL> --force-download
```
- **Sempre usa** estratégia `download_upload`
- **Sempre extrai áudio** de vídeos
- Arquivos MP3 são salvos na pasta do canal

### Clonagem para Canal Existente
```bash
python main.py sync --origin <ID_DO_CANAL> --dest <ID_CANAL_DESTINO>
```
- Usa um canal de destino existente em vez de criar um novo
- Útil para continuar clonando em um canal já existente

### Clonagem e Sair do Canal de Origem
```bash
python main.py sync --origin <ID_DO_CANAL> --leave-origin
```
- Sai automaticamente do canal de origem após a clonagem
- Por padrão, permanece no canal de origem

### Combinações de Opções
```bash
# Clonagem completa: extrair áudio, usar canal existente e sair do origem
python main.py sync --origin <ID_DO_CANAL> --force-download --dest <ID_DESTINO> --leave-origin

# Clonagem simples para canal existente
python main.py sync --origin <ID_DO_CANAL> --dest <ID_DESTINO>
```

### Clonagem em Lote
```bash
python main.py sync --batch --source arquivo_com_ids.txt
```

### Clonagem em Lote com Extração de Áudio
```bash
python main.py sync --batch --source arquivo_com_ids.txt --force-download
```

### Modo Restart (Força Nova Clonagem)
```bash
python main.py sync --origin <ID_DO_CANAL> --restart
```

### Verificar Versão
```bash
python main.py version
```

### Inicializar Banco de Dados
```bash
python main.py init-database
```
- Inicializa ou atualiza o banco de dados
- Cria as tabelas necessárias (SyncTasks e DownloadTasks)
- Útil após atualizações que adicionam novas tabelas

### Listar Chats Disponíveis
```bash
python main.py list-chats
```
- Lista todos os chats, grupos e canais que o usuário tem acesso
- Mostra ID, nome e tipo de cada chat
- Útil para verificar IDs corretos dos canais

### Testar Resolução de Chat
```bash
python main.py test-resolve --id <ID_DO_CANAL>
```
- Testa se um ID, username ou link de chat pode ser resolvido
- Verifica se o usuário tem acesso ao chat
- Útil para diagnosticar problemas de acesso

### Download de Vídeos com Extração de Áudio
```bash
python main.py download --origin <ID_DO_CANAL>
```
- Baixa todos os vídeos de um canal
- Extrai automaticamente o áudio de cada vídeo em MP3
- Mantém tanto o vídeo quanto o áudio
- Salva os arquivos organizados por data e ID da mensagem
- **Resume automaticamente** de onde parou se interrompido

### Download com Limite de Vídeos
```bash
python main.py download --origin <ID_DO_CANAL> --limit 10
```
- Baixa apenas os 10 vídeos mais recentes
- Útil para testar ou baixar apenas alguns vídeos

### Download para Diretório Específico
```bash
python main.py download --origin <ID_DO_CANAL> --output ./meus_videos/
```
- Salva os arquivos em um diretório específico
- Por padrão, salva em `./downloads/Nome_do_Canal/`

### Download com Restart (Força Novo Download)
```bash
python main.py download --origin <ID_DO_CANAL> --restart
```
- Força um novo download do zero
- Apaga dados anteriores de progresso
- Útil quando quer recomeçar completamente

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
- **Extração de Áudio**: Vídeos são processados para extrair áudio em MP3
- **Força Download**: Opção `--force-download` para sempre extrair áudio
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
**Solução**: Execute `python main.py init-database` para criar as tabelas necessárias.

### Erro de acesso a chat
```
Cannot resolve chat identifier
```
**Solução**: 
- Verifique se você é membro do canal/grupo
- Use `python main.py list-chats` para ver os chats disponíveis
- Use `python main.py test-resolve --id <ID>` para testar acesso específico

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
- Use `--force-download` para garantir extração de áudio de todos os vídeos
- Os arquivos MP3 extraídos são preservados na pasta do canal
- Por padrão, o sistema **não sai** do canal de origem (use `--leave-origin` se necessário)
- Ao usar `--dest`, certifique-se de ter permissões de escrita no canal de destino 

## 💡 Exemplos Práticos

### Fluxo Completo de Clonagem
```bash
# 1. Verificar acesso ao canal
python main.py test-resolve --id -1002859374479

# 2. Clonar com extração de áudio
python main.py sync --origin -1002859374479 --force-download

# 3. Verificar links salvos
cat links_canais.txt
```

### Fluxo de Download de Vídeos
```bash
# 1. Listar canais disponíveis
python main.py list-chats

# 2. Baixar vídeos com limite
python main.py download --origin -1002859374479 --limit 5

# 3. Se interrompido, retomar automaticamente
python main.py download --origin -1002859374479

# 4. Para forçar novo download
python main.py download --origin -1002859374479 --restart
```

### Diagnóstico de Problemas
```bash
# Verificar versão
python main.py version

# Inicializar banco de dados
python main.py init-database

# Testar acesso específico
python main.py test-resolve --id @canal_username

# Listar todos os chats
python main.py list-chats
```

### Uso Avançado
```bash
# Clonar para canal existente
python main.py sync --origin -1002859374479 --dest -1002749622339

# Clonar e sair do canal origem
python main.py sync --origin -1002859374479 --leave-origin

# Download para diretório específico
python main.py download --origin -1002859374479 --output ./meus_videos/

# Processamento em lote
python main.py sync --batch --source canais.txt
``` 