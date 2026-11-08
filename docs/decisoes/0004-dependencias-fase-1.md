# ADR 0004: dependências da Fase 1

- Status: aceita
- Data: 2026-11-08

Toda biblioteca tem um propósito (regra 10). Versões fixadas em `requirements.txt` e `requirements-dev.txt`.

| Biblioteca | Licença | Para quê |
| --- | --- | --- |
| `httpx` | BSD-3 | Cliente HTTP do coletor, com timeout e streaming; testável com `respx` |
| `tenacity` | Apache-2.0 | Novas tentativas com espera crescente, só para erros transitórios (429, 5xx, rede) |
| `sqlalchemy` | MIT | ORM e acesso ao banco (PostgreSQL em produção, SQLite nos testes) |
| `alembic` | MIT | Migrações versionadas do banco |
| `psycopg[binary]` | LGPL-3.0 | Driver do PostgreSQL; usado como biblioteca sem modificação, o que a LGPL permite em projeto MIT |
| `pydantic` | MIT | Validação de dados e da saída do LLM |
| `pydantic-settings` | MIT | Configuração lida do `.env`, com segredos em `SecretStr` |
| `python-dotenv` | BSD-3 | Leitura do `.env` nos scripts de verificação da Fase 0 |
| `openai` | Apache-2.0 | SDK do LLM (endpoint compatível do Gemini) |
| `pypdfium2` | Apache-2.0 / BSD-3 | Renderização das páginas do PDF |
| `pytesseract` | Apache-2.0 | Interface com o Tesseract (OCR) |
| `pytest` | MIT | Testes |
| `respx` | BSD-3 | Dublê do PNCP nos testes (`FakePNCP`), sem chamar a API real |
| `ruff` | MIT | Lint e formatação |

## Observações

- `psycopg` usa LGPL-3.0, que não é das licenças preferidas (MIT, BSD, Apache). Registrado aqui conforme a
  regra 10. A alternativa seria `pg8000` (BSD), mais lenta e menos usada; não compensa.
- A imagem do PostgreSQL é fixada na versão principal (`postgres:17-alpine`).
