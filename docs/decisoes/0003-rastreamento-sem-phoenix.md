# ADR 0003: rastreamento com painel próprio, sem Phoenix

- Status: aceita (2026-11-08)
- Data: 2026-11-07

## Contexto

A seção 9.2 prevê exportar traces para o Arize Phoenix se ele rodar bem na máquina; senão, um painel próprio.
A máquina tem 8 GB de RAM, que já serão divididos entre Docker (PostgreSQL), Ollama e VS Code.

## Decisão

Não usar o Phoenix. Cada chamada de LLM e cada passo do agente ficam registrados na tabela `llm_calls`
(com correlation id, tempo, tokens e custo), e a demo tem um painel de operação lido dessa tabela.

## Consequências

- Uma dependência e um contêiner a menos.
- Sem a visualização em árvore do Phoenix; o painel próprio mostra os passos por correlation id.
- A instrumentação pode ganhar exportação OpenTelemetry depois, sem mudar a tabela.
