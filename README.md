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

## 📁 Estrutura do Projeto

```
chatclone/
├── data/
│   ├── clonechat.db         # Banco de dados SQLite
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

### Arquivo de Links dos Canais
Após cada clonagem, o arquivo `links_canais.txt` é atualizado com:
```
Nome do Canal Original
https://t.me/c/1234567890/1
Nome do Canal Original 2
https://t.me/c/9876543210/1
```

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

### Áudio não sendo extraído
**Problema**: Usando estratégia `forward` que não extrai áudio.
**Solução**: Use a opção `--force-download` para forçar extração de áudio.

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
- O arquivo `.env` **não** deve ser versionado
- Use o modo `--restart` com cuidado, pois apaga dados anteriores
- O sistema cria automaticamente canais de destino (a menos que `--dest` seja especificado)
- Use `--force-download` para garantir extração de áudio de todos os vídeos
- Os arquivos MP3 extraídos são preservados na pasta do canal
- Por padrão, o sistema **não sai** do canal de origem (use `--leave-origin` se necessário)
- Ao usar `--dest`, certifique-se de ter permissões de escrita no canal de destino 