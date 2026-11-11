# ContratoLens

**IA que lê contratos públicos, extrai o que importa e responde perguntas citando a página.**

> Projeto de portfólio em construção. Acompanhe o andamento em [`docs/progresso.md`](docs/progresso.md).
> Os números finais (acerto por campo, custo por mil documentos, recall@5) entram aqui quando forem
> medidos por scripts versionados.

## O que é

Uma consultoria acompanha milhares de contratos públicos. O ContratoLens baixa os contratos do
[PNCP](https://pncp.gov.br) (Portal Nacional de Contratações Públicas), lê os PDFs (com OCR quando são
escaneados), extrai valor, vigência, reajuste, multa e garantia com LLM, mede o acerto contra o dado
oficial do portal e responde perguntas sobre a base sempre citando contrato e página.

## Status

| Fase | Situação |
| --- | --- |
| 0. Verificação da fonte e do ambiente | Concluída ([registro](docs/setup-verificacao.md)) |
| 1. Fundação e coleta | Concluída: 174.956 contratos de out/2026 no banco, 1.000 com PDF |
| 2. Leitura dos documentos | Próxima |

## Como rodar (Windows, PowerShell)

Pré-requisitos: Python 3.11, Docker Desktop, Git. Detalhes em [`docs/setup-verificacao.md`](docs/setup-verificacao.md).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env   # depois preencha o .env
docker compose up -d db
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\pytest.exe
```

## Coleta

```powershell
# 1. Levantamento só com metadados (não baixa PDFs)
.\.venv\Scripts\python.exe scripts\levantar_recorte.py --inicio 2026-10-01 --fim 2026-10-07 --amostra 100

# 2. Coleta do recorte (pode ser interrompida e retomada com o mesmo comando)
.\.venv\Scripts\python.exe scripts\coletar.py --inicio 2026-05-01 --fim 2026-10-31 --ufs TO --meta 3000
```

## Fonte dos dados

Dados públicos do [Portal Nacional de Contratações Públicas (PNCP)](https://pncp.gov.br), obtidos pela
API pública oficial, com intervalo entre chamadas e identificação genérica do cliente. Os documentos
baixados ficam fora do repositório.

## Licença

MIT. Veja [`LICENSE`](LICENSE).
