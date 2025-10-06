# Requisitos Funcionais do Clonechat

Este documento detalha os requisitos funcionais da aplicação Clonechat, derivados da análise do código-fonte e dos comandos da CLI.

## Clonagem de Chats (`sync`)

- **RF01:** O sistema deve permitir a clonagem de um chat do Telegram (origem) para um novo canal privado (destino).
- **RF02:** O sistema deve permitir a clonagem para um canal de destino já existente, especificado pelo usuário.
- **RF03:** O sistema deve suportar a clonagem de múltiplos chats em modo lote, lendo os IDs de origem de um arquivo de texto.
- **RF04:** O sistema deve detectar automaticamente se o chat de origem possui restrição de encaminhamento de mensagens.
- **RF05:** O sistema deve aplicar a estratégia de "forward" (encaminhamento direto) para chats sem restrição, para maior eficiência.
- **RF06:** O sistema deve aplicar a estratégia de "download-upload" para chats com restrição de encaminhamento.
- **RF07:** O usuário deve poder forçar a utilização da estratégia "download-upload" através de uma flag (`--force-download`).
- **RF08:** O sistema deve permitir a extração de áudio de arquivos de vídeo durante a clonagem, quando a estratégia "download-upload" é utilizada (`--extract-audio`).
- **RF09:** O sistema deve ser capaz de resumir uma tarefa de clonagem do ponto onde parou em caso de interrupção.
- **RF10:** O usuário deve poder forçar o reinício de uma tarefa de clonagem, apagando todo o progresso anterior (`--restart`).
- **RF11:** O sistema deve permitir que o usuário saia automaticamente do canal de origem após a conclusão da clonagem (`--leave-origin`).
- **RF12:** O sistema deve ser capaz de publicar o link do canal clonado em um chat ou grupo específico (`--publish-to`).
- **RF13:** Ao publicar em um grupo com tópicos, o sistema deve permitir a especificação de um tópico de destino (`--topic`).
- **RF14:** O sistema deve replicar as mensagens fixadas do chat de origem no chat de destino após a clonagem.
- **RF15:** O sistema deve validar a existência e o acesso aos chats de origem antes de iniciar um processo em lote, ignorando IDs inválidos.
- **RF16:** O sistema deve atualizar seu cache de diálogos no início do processo de `sync` para garantir que novos canais na conta do usuário sejam reconhecidos.

## Download de Mídia (`download`)

- **RF17:** O sistema deve permitir o download de todos os vídeos de um canal especificado.
- **RF18:** O sistema deve extrair o áudio dos vídeos baixados, salvando-os em formato MP3.
- **RF19:** O usuário deve poder limitar a quantidade de vídeos a serem baixados (`--limit`).
- **RF20:** O usuário deve poder especificar um diretório de saída para os arquivos baixados (`--output`).
- **RF21:** O sistema deve ser capaz de resumir uma tarefa de download do ponto onde parou.
- **RF22:** O usuário deve poder forçar o reinício de uma tarefa de download (`--restart`).
- **RF23:** O sistema deve permitir a exclusão do arquivo de vídeo original após a extração bem-sucedida do áudio (`--delete-video`).
- **RF24:** O usuário deve poder especificar uma mensagem de início (`--message-id`) para o processo de download.

## Publicação de Conteúdo (`publish`)

- **RF25:** O sistema deve permitir a publicação do conteúdo de uma pasta local em um novo canal do Telegram.
- **RF26:** O sistema deve executar um pipeline de processamento que inclui as seguintes etapas:
    - **Compactação:** Comprimir arquivos (exceto vídeos) em partes de tamanho definido.
    - **Relatório:** Gerar um arquivo CSV com metadados detalhados dos vídeos na pasta.
    - **Re-codificação:** Re-codificar vídeos com base em um plano definido no relatório para otimização.
    - **Junção/Finalização:** Agrupar múltiplos vídeos em um só ou finalizar arquivos individuais, conforme o plano.
    - **Timestamps:** Gerar um sumário (`summary.txt`) com a estrutura do conteúdo e um plano de upload (`upload_plan.csv`).
    - **Upload:** Enviar os arquivos processados para o canal de destino no Telegram.
- **RF27:** O sistema deve ser capaz de resumir um processo de publicação a partir da última etapa concluída.
- **RF28:** O usuário deve poder forçar o reinício do processo de publicação (`--restart`).
- **RF29:** O sistema deve publicar o link do canal criado em um chat, grupo ou tópico específico.
- **RF30:** O sistema deve gerar uma descrição para o canal de destino contendo metadados como tamanho total e duração total do conteúdo.
- **RF31:** O sistema deve fixar a mensagem de sumário no canal de destino após o upload de todo o conteúdo.

## Utilitários da CLI

- **RF32:** O sistema deve fornecer um comando para listar todos os chats dos quais o usuário faz parte (`list-chats`).
- **RF33:** O sistema deve fornecer um comando para listar todos os tópicos de um grupo específico (`list-topics`).
- **RF34:** O sistema deve fornecer um comando para testar a resolução de um identificador de chat (ID, username, link) para seu ID numérico (`test-resolve`).
- **RF35:** O sistema deve fornecer um comando para inicializar as tabelas do banco de dados (`init-database`).
- **RF36:** O sistema deve fornecer um comando para exibir a versão atual da aplicação (`version`).

## Configuração e Ambiente

- **RF37:** O sistema deve carregar as credenciais da API do Telegram e outras configurações a partir de um arquivo `.env`.
- **RF38:** O sistema deve verificar se dependências externas, como o FFmpeg, estão instaladas e disponíveis no PATH do sistema.
