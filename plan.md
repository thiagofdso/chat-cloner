# Plano para eliminar cópia de vídeos antes do upload

## Objetivo
Permitir que o pipeline publique diretamente os arquivos originais, recodificados, divididos ou agrupados sem duplicá-los em `output_videos`, mantendo o plano de upload consistente e evitando desperdício de disco.

## Contexto atual
- `output_videos` recebe ZIPs (etapa 1) e os vídeos finais copiados na etapa 4 (`_step_join`).
- O plano de upload (etapa 5) e o upload (etapa 6) assumem que todo o material final está dentro de `output_videos`.
- O relatório `video_details.csv` contém os caminhos originais; versões split (`videos_splitted`) e recodificadas (`videos_encoded`) ficam cada uma em seu diretório dedicado.

## Etapa 1 – Ajustar `_step_join` para gerar manifesto em vez de copiar
- [ ] Introduzir um manifesto (por exemplo `final_media_manifest.csv`) contendo colunas: `original_name`, `final_path`, `final_type` (`original|split|reencode|grouped`), `order_hint`.
- [ ] Ao final da etapa, preencher o manifesto com o caminho absoluto real de cada arquivo selecionado (original, split, encoded ou arquivo agrupado).
- [ ] Garantir que o manifesto também liste eventuais arquivos agrupados gerados pelo `vidtool.set_join_videos` (modo `group`) apontando para a saída real da biblioteca.
- [ ] Manter `output_videos` apenas para os ZIPs existentes; remover a cópia dos vídeos originais.
- [ ] Atualizar logs para deixar claro que os arquivos finais não são duplicados, apenas referenciados.

## Etapa 2 – Atualizar geração de timestamps/summary/upload plan
- [ ] Alterar `_step_timestamp` para consumir o manifesto ao invés de vasculhar `output_videos`.  
      - Utilizar a coluna `final_path` para montar `ordered_video_files`.  
      - Continuar aceitando ZIPs direto de `output_videos` (sem alterações).
- [ ] Ao criar `files_to_upload`, gravar tanto ZIPs quanto itens do manifesto, preservando a ordem definida na etapa anterior.
- [ ] Validar que a estrutura do summary (`summary.txt`) mostre corretamente as subpastas originais usando `final_path.relative_to(self.source_folder)` quando possível.

## Etapa 3 – Adequar `_read_upload_plan` e `_upload_file`
- [ ] Garantir que `upload_plan.csv` salve o caminho absoluto (ou relativo ao projeto) vindo do manifesto para cada vídeo.
- [ ] Ajustar `_read_upload_plan` para normalizar caminhos relativos (ex.: se começar com `source://`, converter para `Path(self.source_folder) / …`).
- [ ] Confirmar que `_upload_file` funcione com qualquer local real (originais, splits, codificados ou grouped) e que não dependa mais de `output_videos`.

## Etapa 4 – Migração e compatibilidade
- [ ] Adicionar fallback: se o manifesto não existir (tarefas antigas), seguir o fluxo atual baseado em `output_videos`.
- [ ] Atualizar documentação/logs para orientar o usuário sobre o novo comportamento.
- [ ] Validar espaço em disco: remover ou tornar opcional a limpeza de `output_videos` agora que não recebe mais cópias.

## Etapa 5 – Testes e validação manual
- [ ] Rodar `poetry run python main.py publish -r -f "<pasta>"` em um projeto pequeno garantindo que `upload_plan.csv` referencie arquivos reais.
- [ ] Verificar que `summary.txt` lista corretamente os caminhos originais.
- [ ] Confirmar via logs que nenhuma cópia para `output_videos` ocorreu e que o upload envia arquivos válidos.

