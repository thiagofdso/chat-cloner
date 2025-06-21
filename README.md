# Clonechat

Ferramenta avançada para clonar chats do Telegram.

## Pré-requisitos

- **Python 3.9+**
- **FFmpeg** instalado e disponível no PATH do Windows
    - Baixe em: https://ffmpeg.org/download.html
    - Adicione o executável à variável de ambiente PATH
- **Build Tools do Visual Studio (VSCode)** para instalar a biblioteca `tgcrypto`
    - Instale via: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- **Credenciais do Telegram** (API ID e API Hash)
    - Obtenha em: https://my.telegram.org/apps

## Instalação

1. Instale as dependências do projeto:
```bash
poetry install
```

2. Copie o arquivo `.env.example` para `.env` e preencha com suas credenciais:
```bash
copy .env.example .env
# Edite o arquivo .env e insira seu TELEGRAM_API_ID e TELEGRAM_API_HASH
```

3. Execute o projeto:
```bash
python main.py sync --origin <ID_DO_CANAL>
```

## Uso

- Para clonar um chat individual:
  ```bash
  python main.py sync --origin <ID_DO_CANAL>
  ```
- Para clonar vários chats em lote:
  ```bash
  python main.py sync --batch --source arquivo_com_ids.txt
  ```

## Observações
- O FFmpeg **deve** estar instalado e disponível no PATH antes de rodar o projeto.
- O Build Tools do Visual Studio é necessário para instalar a dependência nativa `tgcrypto`.
- O arquivo `.env` **não** deve ser versionado. 