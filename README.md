# Clonechat

Telegram chat cloning tool with advanced features.

## Instalação

1. Instale as dependências:
```bash
poetry install
```

2. Configure suas credenciais do Telegram no arquivo `config.ini`

3. Execute o projeto:
```bash
python main.py sync --origin <ID_DO_CANAL>
```

## Requisitos

- Python 3.9+
- FFmpeg instalado e disponível no PATH
- Credenciais do Telegram (API ID e API Hash) 