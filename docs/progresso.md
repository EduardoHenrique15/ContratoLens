# Progresso do ContratoLens

| Fase | Status | Data |
| --- | --- | --- |
| Fase 0: verificação e ambiente | Concluída | 2026-11-07 |
| Fase 1: fundação e coleta | Não iniciada | |
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

- Confirmar a ADR 0003 (rastreamento sem Phoenix).
- Registrar o preço por token do `gemini-3.8-flash` antes da estimativa de custo da Fase 3.
- Procurar a licença explícita dos dados do PNCP antes da Fase 8.
- Apagar `%TEMP%\contrato_teste.pdf` quando não for mais útil.
