# Progresso do ContratoLens

| Fase | Status | Data |
| --- | --- | --- |
| Fase 0: verificação e ambiente | Concluída | 2026-11-07 |
| Fase 1: fundação e coleta | Concluída | 2026-11-11 |
| Fase 2: leitura de documentos | Não iniciada | |
| Fase 3: extração com LLM e validações | Não iniciada | |
| Fase 4: conjunto de referência e comparação | Não iniciada | |
| Fase 5: busca e agente | Não iniciada | |
| Fase 6: LLMOps e API | Não iniciada | |
| Fase 7: demo e revisão humana | Não iniciada | |
| Fase 8: diferenciais | Não iniciada | |
| Fase 9: documentação e lançamento | Não iniciada | |

## Fase 0: verificação e ambiente

Checklist (seção 13 do `CLAUDE.md`):

- [x] 1. API do PNCP: rotas de contratos, campos, rota de arquivos (PDF), limites
- [x] 2. Chave do LLM e suporte a saída estruturada (chamada autorizada)
- [x] 3. Tesseract com idioma `por` no Windows
- [x] 4. Ollama e escolha do modelo local (com medição de velocidade)
- [x] 5. Docker Desktop funcionando; teste opcional do Phoenix
- [x] 6. Conta no Hugging Face
- [x] 7. Registro em `docs/setup-verificacao.md`

### Observações

- A sessão do Claude Code roda na nuvem e não alcança `pncp.gov.br` (bloqueio de rede do ambiente).
  Por isso os testes da API são feitos pelo Eduardo no PowerShell, e a saída é colada na conversa.
- O projeto fica em uma pasta sincronizada pelo OneDrive, por escolha do Eduardo. Na Fase 1, a pasta de dados
  (PDFs baixados) fica fora do OneDrive, configurada por `DATA_DIR` no `.env`, para não sincronizar gigabytes.

### O que foi feito

Todos os itens verificados e registrados em `docs/setup-verificacao.md`; explicação em `docs/aprendizado.md`;
decisões em `docs/decisoes/0001` a `0003`.

### Pendências

- Registrar o preço por token do `gemini-3.8-flash` antes da estimativa de custo da Fase 3.
- Procurar a licença explícita dos dados do PNCP antes da Fase 8.
- Apagar `%TEMP%\contrato_teste.pdf` quando não for mais útil.

## Fase 1: fundação e coleta

Checklist (seção 13):

- [x] 1. Estrutura, `pyproject.toml`, requirements, `.gitignore`, `.env.example`, LICENSE, CI
- [x] 2. `core/` (config, logs, erros, custos, mascaramento) com testes
- [x] 3. Banco, modelos e migração inicial (`contracts`, `documents`, `ingest_jobs`)
- [x] 4. Coletor do PNCP com fila, limite de taxa, novas tentativas, idempotência e retomada; testes com `FakePNCP`
- [x] 5. Levantamento do recorte, coleta e números reais anotados (feito pelo Eduardo, com autorização)

Observações:

- ADR 0003 (rastreamento sem Phoenix) aceita: o Eduardo pediu para prosseguir com o plano.
- 42 testes passando (`pytest`), `ruff check` e `ruff format` limpos.
- O teste da migração contra o PostgreSQL real é feito na máquina do Eduardo (`alembic upgrade head`).
- Migração 0001 aplicada no PostgreSQL do Eduardo em 2026-11-08.
- Levantamento real (semana de 1 a 7/10/2026): 42.137 registros; cobertura de PDF de 80% entre os que
  responderam; rota de arquivos lenta (mediana 51 s) e instável (37% de erro na amostra).
  Recorte proposto na ADR 0006: cerca de 1.000 contratos de outubro de 2026, todo o país.

### Resultado da coleta (`scripts/estatisticas_coleta.py`, `eval/results/coleta_20261111.json`)

| Medida | Valor |
| --- | --- |
| Contratos de outubro de 2026 no banco (metadados oficiais) | 174.956 |
| Contratos com PDF de contrato baixado | 1.000 (meta atingida) |
| Documentos baixados | 1.026 (1.015 PDFs; 11 arquivos que não são PDF) |
| Contratos sem PDF do tipo "Contrato" | 244 |
| Cobertura de PDF entre os contratos consultados | 80,4% |
| Consultas que falharam após todas as tentativas | 271 de 1.515 (17,9%) |
| Tamanho total / médio / mediano | 0,96 GB / 0,93 MB / 0,10 MB |
| Esfera dos baixados | municipal 730, federal 134, estadual 117 |
| UFs com mais contratos baixados | SC 328, SP 154, MG 69, GO 66, PR 66 |

Pendências para a Fase 2:

- Tratar os 11 arquivos que não começam com `%PDF` (identificar o formato e registrar).
- As 271 consultas com falha podem voltar à fila com `--refazer-falhas`, se for preciso aumentar a base.
- O tamanho mediano de 0,10 MB sugere que boa parte dos PDFs tem texto nativo (sem OCR); medir na Fase 2.
