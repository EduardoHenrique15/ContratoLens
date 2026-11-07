# CLAUDE.md: ContratoLens

> Instruções permanentes para o Claude Code neste repositório. Este arquivo é lido automaticamente em toda sessão.

## Quando o Eduardo escrever "Faça esse projeto"

Execute o projeto descrito na **Especificação** abaixo, seguindo estas regras de execução:

1. **Descubra onde parou.**
   - Leia `docs/progresso.md`.
   - Se o arquivo não existir, crie-o e comece pela **Fase 0**.
   - Se existir, continue da primeira fase que ainda não está marcada como concluída.
2. **Uma fase por vez, na ordem da seção 13.**
   - Só avance quando o "critério de pronto" da fase estiver cumprido e verificado: rode `ruff check .`, `ruff format .` e `pytest`.
3. **Passos manuais.**
   - Você não consegue criar contas, clicar em consoles nem instalar programas no Windows do Eduardo.
   - Guie o Eduardo **um passo por vez**, com instruções exatas em português (links, onde clicar, o que copiar e onde colar no `.env`).
   - Espere ele confirmar cada passo antes de seguir.
4. **Rotulagem de referência.**
   - A Fase 4 exige que o Eduardo monte o conjunto de referência das cláusulas. Prepare a ferramenta e o guia, explique e espere.
   - **Nunca** preencha o conjunto de referência com saídas do LLM nem invente rótulos. Se o Eduardo usar apoio de IA, isso é registrado em ADR e no README.
5. **Ao final de cada fase:**
   - atualize `docs/progresso.md`, com a fase concluída, a data, o que foi feito e as pendências;
   - escreva a explicação da fase em `docs/aprendizado.md`, em português simples, para o Eduardo conseguir explicar cada decisão em entrevistas;
   - mostre ao Eduardo um resumo curto: o que foi feito, a saída dos testes, os números principais e o que vem a seguir;
   - **pare e pergunte se pode seguir para a próxima fase.**
6. **Fluxo de trabalho com o Git:** faça commits locais pequenos ao fim de cada fase aprovada. **Nunca** faça `git push` sem autorização explícita.
7. **Cota e custo do LLM:** nunca chame o LLM real sem pedir. Nos testes, use sempre o LLM falso. Antes de qualquer execução em lote, mostre a estimativa de chamadas, tokens e custo em reais, e espere a autorização.
8. **Quando a realidade divergir da especificação** (a API não entrega um campo, um limite é diferente, uma biblioteca mudou): explique, proponha uma alternativa, registre em `docs/decisoes/` e siga.
9. **Honestidade nos números:** todo número publicado no README, no relatório, no site ou no post vem de um script versionado que o reproduz. Resultados ruins também são publicados e explicados.

---

# Especificação

## 0. Como usar este documento (leia primeiro, Claude Code)

1. Leia o documento inteiro antes de escrever qualquer código.
2. Siga as fases na ordem da seção 13.
3. Respeite as regras da seção 2, sempre.
4. Este é um projeto de portfólio que simula o trabalho real de um **engenheiro de IA** numa empresa: processar documentos em volume, medir a qualidade com gabarito, operar LLMs com custo controlado e entregar um produto que outra pessoa consegue usar. Cada decisão deve ser justificada por qualidade, custo, latência ou risco.
5. **Prioridade:** o nível Essencial (seção 1.4) completo, testado e documentado vem antes de qualquer extra. Se o tempo apertar, corte na ordem da seção 16.

---

## 1. O projeto

### 1.1 Nome e frase de efeito
**ContratoLens: IA que lê contratos públicos, extrai o que importa e responde perguntas citando a página.**

Repositório: `contratolens`. Pacote Python: `contratolens`.

### 1.2 Contexto de negócio (cenário)
Uma consultoria acompanha milhares de contratos públicos para clientes (fornecedores do governo, escritórios de advocacia e jornalistas de dados). Hoje:
- analistas abrem cada PDF à mão para achar valor, vigência, reajuste, multa e garantia;
- ninguém sabe, de forma rápida, quais contratos vencem nos próximos meses;
- divergências entre o que está no PDF e o que foi cadastrado no portal passam despercebidas.

**Objetivo:** reduzir o tempo de análise por contrato sem perder precisão, e permitir perguntas em linguagem natural sobre a base inteira, sempre com a fonte.

**Métricas de negócio que o projeto mede:**
- acerto por campo extraído (comparado ao dado oficial e ao conjunto de referência);
- custo em reais por mil documentos;
- tempo por documento (p50 e p95);
- porcentagem de documentos resolvidos sem revisão humana, e o acerto dentro desse grupo;
- qualidade das respostas do agente (fidelidade e citação correta).

### 1.3 O que torna o projeto atrativo (para recrutadores e para quem vê o post)
1. **Demo pública** que qualquer pessoa abre no navegador: escolhe um contrato e vê os campos extraídos **destacados em cima do PDF**, com a página e o trecho.
2. **Gabarito real em escala:** a avaliação usa o dado oficial do portal como verdade para milhares de contratos, não só um punhado de exemplos.
3. **Benchmark de modelos** publicado: regras contra LLM de ponta contra modelo local, com acerto, custo e latência lado a lado.
4. **Agente que responde perguntas sobre a base** ("quais contratos de TI acima de R$ 1 milhão vencem em 60 dias?") citando contrato e página.
5. **Servidor MCP**: o Claude Desktop usa as ferramentas do ContratoLens direto. Vídeo curto mostrando isso.
6. **LLMOps de verdade:** gateway com fallback, orçamento, rastreamento de cada chamada e avaliação no CI.
7. **Achados de qualidade de dados:** contratos em que o valor do PDF não bate com o valor cadastrado, sem acusar ninguém.
8. **Conjunto de dados aberto:** os campos extraídos publicados como dataset, com documentação, para a comunidade usar.
9. **Documentação de time de produto:** design doc, runbook, postmortem simulado, model cards e ADRs.

### 1.4 Níveis de entrega

| Nível | Conteúdo | Prioridade |
| --- | --- | --- |
| Essencial | Ingestão do PNCP, leitura de PDF (com OCR quando precisar), extração estruturada com LLM, validações, avaliação contra o dado oficial, revisão humana por confiança, API, demo com destaque no PDF, testes, README e design doc | Obrigatório |
| Avançado | Comparação com regras e modelo local, conjunto de referência das cláusulas, RAG com reranker e métricas de recuperação, agente com ferramentas, gateway com fallback e orçamento, rastreamento, avaliação no CI | Desejável |
| Diferencial | Servidor MCP, teste de carga, red team, achados de qualidade de dados, dataset aberto, alerta semanal no n8n, runbook e postmortem, vídeo e post | Destaque |

### 1.5 Regra de ouro
**Nada inventado.** Todo campo extraído aponta para a página e o trecho de onde saiu. O agente nunca responde sem citar a fonte. Nenhum achado é apresentado como irregularidade: divergências são "inconsistências de cadastro a verificar".

### 1.6 Entregáveis
1. Repositório público com README em português, GIF da demo e seção de números no topo.
2. Demo pública no navegador.
3. `docs/design-doc.md`, `docs/runbook.md`, `docs/postmortem-simulado.md`.
4. Model cards em `docs/model-cards/` (extração e agente).
5. `docs/benchmark.md` com a comparação de abordagens.
6. `docs/relatorio-custos.md` com custo por mil documentos.
7. ADRs em `docs/decisoes/`.
8. Dataset aberto com documentação (data card).
9. Servidor MCP com instruções para o Claude Desktop.
10. Vídeo curto e texto do post no LinkedIn em `docs/post-linkedin.md`.

---

## 2. Regras do projeto (valem sempre)

1. **Segredos:**
   - nunca leia, imprima, registre em log ou versione `.env`, chaves de API ou tokens;
   - para saber se uma variável existe, verifique só o nome;
   - `.gitignore` cobre `.env`, `data/`, `models/`, `.cache/`, `.llm_cache/`, `.chroma/` e volumes do Docker desde o primeiro commit.
2. **Git:** sem `git push` sem autorização; commits pequenos, em português, no padrão `tipo: descrição` (ex.: `feat: cria extrator de vigência`).
3. **Custo do LLM:**
   - testes automatizados usam **sempre** o LLM falso;
   - toda chamada real passa pelo gateway (seção 9), com cache em disco e orçamento diário;
   - execuções em lote só com autorização e estimativa de custo mostrada antes.
4. **Respeito à fonte de dados:**
   - use só a API pública oficial do PNCP, respeitando limites de requisição, com espera entre chamadas e identificação genérica do cliente (sem e-mail pessoal);
   - guarde os documentos baixados fora do git;
   - cite a fonte no README e no dataset.
5. **Dados pessoais:**
   - mascare CPF de pessoas físicas e e-mails e telefones pessoais antes de enviar texto ao LLM e antes de publicar qualquer dado;
   - o dataset aberto não contém CPF de pessoa física nem nomes de pessoas físicas;
   - CNPJ de empresas e nomes de órgãos são dados públicos e podem aparecer.
6. **Tom dos achados:** nunca acusar órgãos, empresas ou pessoas. Divergências viram "inconsistência a verificar", com a explicação técnica.
7. **Idioma:** README, documentação, interface e mensagens em **português do Brasil**; código em inglês; docstrings em português.
8. **Ambiente do Eduardo:** Windows, PowerShell, VS Code, Python 3.11, Docker Desktop. Todo comando documentado precisa funcionar no PowerShell.
9. **Qualidade mínima:** `ruff check .` limpo, `ruff format .` aplicado, `pytest` passando e arquivos terminando com quebra de linha.
10. **Sem dependência sem propósito:** toda biblioteca nova tem uma linha de justificativa em `docs/decisoes/` ou no README. Prefira licenças permissivas (MIT, BSD, Apache) e registre em ADR quando usar outra.
11. **Reprodutibilidade:** versões fixadas, sementes fixas e cada número publicado gerado por script em `scripts/`.

---

## 3. Decisões técnicas (stack)

| Camada | Escolha | Por quê |
| --- | --- | --- |
| Linguagem | Python 3.11 | Linguagem principal do Eduardo |
| Coleta | `httpx` + fila simples em banco | Cliente HTTP moderno, com timeout e retentativas |
| Retentativas | `tenacity` | Espera crescente só para erros transitórios |
| PDF com texto | `pdfplumber` (texto com coordenadas) + `pypdfium2` (renderizar página) | Licenças permissivas; coordenadas permitem destacar o trecho no PDF |
| OCR | Tesseract (`pytesseract`, idioma `por`) | Gratuito, roda local; só para páginas escaneadas |
| Extração estruturada | LLM via SDK `openai` com endpoint compatível (Gemini ou Groq) + Pydantic | Provedor trocável por configuração; saída validada |
| Modelo local | Ollama com um modelo pequeno (definido na Fase 0 conforme a máquina) | Comparação de custo zero por chamada e privacidade |
| Baseline | Regras e expressões regulares | Referência honesta para medir o ganho do LLM |
| Banco | PostgreSQL (Docker); SQLite nos testes | Contratos, campos extraídos, revisões, chamadas de LLM |
| ORM e migrações | SQLAlchemy 2 + Alembic | Mesmo padrão do Copiloto de Atendimento |
| Embeddings | `sentence-transformers` multilíngue, local | Sem custo por chamada |
| Busca vetorial | ChromaDB local | Simples e já conhecido pelo Eduardo |
| Busca lexical | BM25 (`rank-bm25`) | Busca híbrida com a vetorial |
| Reranker | cross-encoder multilíngue do `sentence-transformers` | Reordena os trechos recuperados |
| API | FastAPI + Uvicorn | Serviço de extração, busca, agente e métricas |
| Servidor MCP | SDK oficial `mcp` (FastMCP) | Expõe as ferramentas para o Claude Desktop |
| Rastreamento | Tabela própria `llm_calls` + Arize Phoenix (opcional, um contêiner) via OpenTelemetry | Ver cada passo do agente com custo e tempo; decidir na Fase 0 |
| Demo | Streamlit | O Eduardo já domina; permite desenhar o destaque sobre a imagem da página |
| Teste de carga | Locust | Mede p95 sob volume |
| Automação (Diferencial) | n8n | Alerta semanal de vencimentos no Telegram, reaproveitando a experiência do Copiloto |
| Testes | `pytest`, `respx` | Unitários, de contrato e de integração com dublês |
| Qualidade e CI | `ruff`, GitHub Actions | Igual aos outros projetos |
| Empacotamento | Docker Compose (`api`, `db`, `worker`, `demo`, `phoenix` opcional) | Reproduzível |
| Hospedagem da demo | Hugging Face Spaces (gratuito) ou Streamlit Community Cloud, em modo leitura | Demo pública sem custo de LLM por visitante |

---

## 4. Arquitetura

### 4.1 Diagrama (Mermaid no README e PNG em `docs/arquitetura.png`)

```mermaid
flowchart LR
    PNCP[API pública do PNCP] --> ING[Coletor\nfila, limite de taxa,\nidempotência]
    ING --> RAW[(PDFs e metadados)]
    RAW --> PARSE[Leitura do PDF\ntexto + coordenadas\nOCR se escaneado]
    PARSE --> EXT[Extração estruturada\nregras | LLM | modelo local]
    EXT --> VAL[Validações\nCNPJ, datas, valor]
    VAL -->|confiança alta| DB[(PostgreSQL)]
    VAL -->|confiança baixa| REV[Fila de revisão humana]
    REV --> DB
    PARSE --> IDX[Indexação de trechos\nBM25 + vetores]
    IDX --> RAG[Busca híbrida\n+ reranker]
    DB --> AG[Agente analista\nferramentas]
    RAG --> AG
    AG --> API[API FastAPI]
    AG --> MCP[Servidor MCP]
    EXT --> GW[Gateway de LLM\nfallback, cache,\norçamento, traces]
    AG --> GW
    API --> DEMO[Demo Streamlit\ndestaque no PDF]
    DB --> N8N[n8n: alerta semanal]
```

### 4.2 Camadas

| Camada | Pasta | Responsabilidade |
| --- | --- | --- |
| Núcleo | `src/contratolens/core/` | Configuração, logs, erros, custos, mascaramento de dados pessoais |
| Coleta | `src/contratolens/ingest/` | Cliente do PNCP, fila, download, idempotência |
| Documentos | `src/contratolens/documents/` | Leitura de PDF, OCR, páginas, trechos com coordenadas |
| Extração | `src/contratolens/extraction/` | Esquema, extratores (regras, LLM, local), validações, confiança |
| Busca | `src/contratolens/retrieval/` | Indexação, BM25, vetores, reranker |
| Agente | `src/contratolens/agent/` | Ferramentas, prompt, laço do agente, guardrails |
| LLM | `src/contratolens/llm/` | Gateway: provedores, fallback, cache, orçamento, traces |
| Avaliação | `src/contratolens/eval/` | Métricas por campo, recuperação, agente, regressão |
| Persistência | `src/contratolens/db/` | Modelos, repositórios, migrações |
| API | `src/contratolens/api/` | Rotas FastAPI |
| MCP | `src/contratolens/mcp_server/` | Ferramentas expostas via MCP |
| Demo | `src/contratolens/demo/` | App Streamlit |

**Regra:** a camada de extração e a de busca **não dependem do agente**. Tudo funciona por script e por API sem o agente, o que facilita testar.

---

## 5. Estrutura de pastas

```
contratolens/
├── README.md
├── LICENSE                         # MIT
├── .gitignore
├── .env.example
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── migrations/
├── src/contratolens/
│   ├── core/
│   ├── ingest/
│   ├── documents/
│   ├── extraction/
│   ├── retrieval/
│   ├── agent/
│   ├── llm/
│   ├── eval/
│   ├── db/
│   ├── api/
│   ├── mcp_server/
│   └── demo/
├── scripts/                        # coleta, extração em lote, avaliação, relatórios, dataset
├── eval/
│   ├── gold/
│   │   ├── guia-de-rotulos.md
│   │   └── clausulas_gold.csv      # conjunto de referência (só ids, campos e páginas)
│   ├── retrieval_questions.yaml    # perguntas com trechos esperados
│   ├── agent_cases.yaml            # casos do agente, incluindo ataques
│   └── results/                    # resultados versionados por data
├── n8n/workflows/                  # alerta semanal (Diferencial)
├── loadtest/                       # Locust
├── docs/
│   ├── design-doc.md
│   ├── benchmark.md
│   ├── relatorio-custos.md
│   ├── runbook.md
│   ├── postmortem-simulado.md
│   ├── model-cards/
│   ├── dataset-card.md
│   ├── arquitetura.png
│   ├── aprendizado.md
│   ├── progresso.md
│   ├── limitacoes.md
│   ├── seguranca.md
│   ├── roteiro-video.md
│   ├── post-linkedin.md
│   └── decisoes/
├── tests/
│   ├── fakes/                      # ScriptedLLM, FakePNCP, PDFs fictícios pequenos
│   ├── unit/
│   ├── contract/
│   └── integration/
└── .github/workflows/ci.yml
```

---

## 6. Dados

### 6.1 Fonte
**PNCP (Portal Nacional de Contratações Públicas)**, pela API pública de consulta. O manual oficial está em `https://pncp.gov.br/manual/` e no portal gov.br do PNCP.

**Na Fase 0, verifique e registre em `docs/setup-verificacao.md`:**
1. quais rotas de consulta de contratos existem e quais filtros aceitam (data, órgão, modalidade);
2. quais campos estruturados vêm em cada contrato (valor, vigência, fornecedor, CNPJ, objeto);
3. **se é possível baixar os arquivos (PDF) de cada contrato**, e por qual rota;
4. limites de requisição e paginação.

**Plano B**, se a API não entregar os PDFs dos contratos: usar os documentos de editais ou atas disponíveis no próprio PNCP, ou outra fonte oficial com documento e metadado (registrar a escolha em ADR). Não use raspagem de sites que proíbem isso.

### 6.2 Recorte
- Um período recente (por exemplo, 6 a 12 meses) e um conjunto de órgãos ou estados definido na Fase 1, mirando **entre 3 mil e 10 mil contratos** com PDF.
- Amostra estratificada por tipo de órgão e por faixa de valor para o conjunto de referência.
- Números reais do recorte anotados em `docs/aprendizado.md`.

### 6.3 Tabelas principais
- `contracts`: id do PNCP, órgão, metadados oficiais (valor, datas, fornecedor, CNPJ, objeto), status do download.
- `documents`: id, contrato, caminho local, hash, páginas, se precisou de OCR.
- `chunks`: id, documento, página, texto, coordenadas (caixa delimitadora).
- `extractions`: id, contrato, extrator (`rules`/`llm`/`local`), versão do prompt, campos extraídos (JSON), confiança por campo, página e trecho por campo, custo e latência.
- `reviews`: id, extração, campo, valor corrigido, revisor, data.
- `llm_calls`: chamada, recurso, provedor, modelo, versão do prompt, tokens, custo em reais, latência, status, correlation id.
- `ingest_jobs`: fila da coleta com status e tentativas.

---

## 7. Extração de documentos

### 7.1 Leitura do PDF
- Extrair texto **com coordenadas** por página (`pdfplumber`).
- Detectar página escaneada (pouco texto extraível) e aplicar OCR só nela, guardando as coordenadas do OCR.
- Dividir em trechos por página e por parágrafo ou cláusula, guardando a caixa delimitadora de cada trecho.
- Guardar o hash do arquivo para idempotência.

### 7.2 Esquema de extração (Pydantic)
Campos com **valor, página, trecho de origem e confiança**:
- `contratante` (órgão) e `contratada` (empresa), com `cnpj_contratada`;
- `objeto` (resumo curto);
- `valor_total` (em reais);
- `data_assinatura`, `vigencia_inicio`, `vigencia_fim`;
- `prazo_meses`;
- `reajuste` (existe? índice, como IPCA ou IGP-M, e periodicidade);
- `multa` (existe? percentual ou descrição);
- `garantia` (existe? modalidade e percentual);
- `foro`;
- `possui_clausula_rescisao`.

### 7.3 Três extratores comparados
1. **Regras:** expressões regulares e heurísticas para valor, datas, CNPJ e palavras-chave das cláusulas.
2. **LLM de ponta:** prompt com o esquema, exemplos curtos e saída estruturada validada por Pydantic. Texto enviado já com dados pessoais mascarados. Envia só as páginas relevantes quando o documento for longo (seleção por busca), e registra isso.
3. **Modelo local (Ollama):** o mesmo prompt num modelo pequeno, para medir até onde vai a qualidade com custo zero por chamada.

### 7.4 Validações determinísticas
- dígito verificador do CNPJ;
- datas válidas e coerentes (fim depois do início; assinatura antes ou no início);
- valor positivo e plausível;
- comparação com o metadado oficial: divergência vira alerta de "inconsistência a verificar", não erro automático (o PDF pode estar certo e o cadastro errado, ou o contrário);
- o trecho citado precisa existir no texto da página indicada.

### 7.5 Confiança e revisão humana
- Confiança por campo combinando: validações passadas, concordância entre extratores e presença do trecho citado.
- Abaixo do limiar configurado, o documento vai para a fila de revisão.
- A demo tem uma tela de revisão: mostra o PDF com o trecho destacado, o valor sugerido e botões para aceitar ou corrigir. A correção é gravada em `reviews`.

---

## 8. Avaliação

### 8.1 Contra o dado oficial (escala)
- Para os campos que o portal também tem (valor, datas, fornecedor, CNPJ, objeto), comparar o extraído com o oficial em **todos** os contratos do recorte.
- Métricas por campo: acerto exato, acerto com tolerância (valor até R$ 1 de diferença; datas iguais), cobertura (campo encontrado ou não).
- Separar resultados por PDF com texto e PDF escaneado.
- Analisar uma amostra de divergências à mão: quantas são erro do extrator e quantas são inconsistência real de cadastro. O número vai para o relatório.

### 8.2 Conjunto de referência das cláusulas
- Cerca de **100 contratos** com as cláusulas (reajuste, multa, garantia, foro, rescisão) anotadas pelo Eduardo na ferramenta de rotulagem da demo, com página e trecho.
- Guia de rótulos em `eval/gold/guia-de-rotulos.md`, com casos de fronteira.
- Divisão em validação (30) e teste (70); o teste só é usado na comparação final.

### 8.3 Benchmark de extração (`docs/benchmark.md`)

| Extrator | Acerto por campo | Custo por mil documentos | Latência p50 / p95 | Observações |
| --- | --- | --- | --- | --- |
| Regras | | R$ 0 | | |
| LLM de ponta | | | | |
| Modelo local | | R$ 0 (custo de máquina estimado) | | |

Inclui gráfico de acerto contra custo e a decisão de produção com justificativa (ADR). Possível arranjo vencedor: regras primeiro e LLM só nos campos que as regras não resolvem com confiança. Medir e decidir pelos números.

### 8.4 Busca (RAG)
- `eval/retrieval_questions.yaml` com cerca de 80 perguntas e o trecho esperado.
- Métricas: recall@5, recall@10 e MRR, comparando vetorial, BM25, híbrida e híbrida com reranker.

### 8.5 Agente
- `eval/agent_cases.yaml` com cerca de 60 casos: perguntas de filtro ("vencem em 60 dias"), de cláusula ("qual o índice de reajuste do contrato X?"), de agregação, perguntas sem resposta na base e 10 tentativas de prompt injection (incluindo texto malicioso dentro de um PDF fictício).
- Critérios automáticos: ferramenta certa chamada, resposta com citação válida (contrato e página existentes), recusa quando não há dado, nenhum vazamento do prompt.
- LLM como juiz só se for validado contra a avaliação do Eduardo em 40 casos (kappa de Cohen ≥ 0,4). Se não passar, o resultado negativo é publicado e o juiz não é usado.

### 8.6 Regressão no CI
- Casos fixos com respostas gravadas (`ScriptedLLM` e cache), cobrindo esquema, validações, citações e guardrails.
- Mudança de prompt registra a versão nova e exige rodar a avaliação real (com autorização), com o antes e depois em `eval/results/`.

---

## 9. Gateway de LLM e observabilidade (LLMOps)

### 9.1 Gateway (`src/contratolens/llm/`)
- Interface única `generate_structured(prompt, schema, feature)` e `chat(messages, tools, feature)`.
- **Provedores configuráveis** com ordem de preferência; **fallback** automático para o próximo em erro persistente ou limite estourado.
- **Cache em disco** por hash da entrada.
- **Retentativas** com espera crescente para 429, 5xx e timeout.
- **Orçamento diário** em reais: ao atingir o limite, o gateway recusa novas chamadas com erro claro (e a extração cai para regras e fila de revisão).
- **Limite de taxa** por provedor.
- Registro de cada chamada em `llm_calls`.

### 9.2 Rastreamento
- Cada extração e cada pergunta ao agente gera um trace com os passos (busca, ferramenta, chamada de LLM), tempo, tokens e custo.
- Exportar via OpenTelemetry para o Arize Phoenix (contêiner opcional) se a Fase 0 confirmar que roda bem na máquina; senão, painel próprio na demo a partir de `llm_calls`.

### 9.3 Métricas (`GET /metrics` e painel)
- custo do dia, da semana e por mil documentos;
- latência p50 e p95 por recurso;
- taxa de fallback, de cache e de recusa por orçamento;
- porcentagem de documentos que foram para revisão;
- taxa de bloqueio dos guardrails do agente.

---

## 10. Busca e agente analista

### 10.1 Busca híbrida
- Indexar os trechos com BM25 e com embeddings.
- Combinar resultados (por exemplo, Reciprocal Rank Fusion) e reordenar com o cross-encoder.
- Filtro por contrato, órgão e período antes da busca.

### 10.2 Ferramentas do agente
1. `buscar_contratos(filtros)`: SQL parametrizado sobre os campos extraídos (órgão, fornecedor, faixa de valor, vigência). **Nunca** SQL livre gerado pelo LLM.
2. `detalhar_contrato(id)`: campos extraídos com página e trecho.
3. `buscar_clausulas(pergunta, filtros)`: busca híbrida com reranker.
4. `contratos_vencendo(dias, filtros)`: cálculo de vencimento.
5. `estatisticas(agrupamento, filtros)`: contagens e somas pré-definidas.

### 10.3 Regras e guardrails do agente
- Toda afirmação sobre um contrato precisa citar `id` e página vindos de uma ferramenta; o código confere se a citação existe antes de devolver a resposta.
- Texto de documentos é **dado, não instrução**; instruções dentro de PDFs são ignoradas e o caso é registrado.
- Sem resposta na base: o agente diz que não encontrou.
- Máximo de passos por pergunta e tempo limite.
- Nenhum dado pessoal na resposta.

### 10.4 Servidor MCP
- Expor as ferramentas da seção 10.2 com o SDK oficial `mcp`.
- `docs/mcp.md` com o passo a passo para configurar no Claude Desktop no Windows.
- Vídeo curto: o Claude Desktop respondendo "quais contratos de limpeza vencem em 30 dias?" usando o ContratoLens.

---

## 11. API (FastAPI)

| Rota | O que faz |
| --- | --- |
| `GET /health` | Status da API e do banco |
| `GET /contracts` | Lista com filtros e paginação |
| `GET /contracts/{id}` | Metadados oficiais, campos extraídos com página, trecho e confiança, divergências |
| `GET /contracts/{id}/pages/{n}` | Imagem da página com as caixas de destaque dos campos |
| `POST /extract` | Extrai um documento (respeitando orçamento e idempotência por hash) |
| `GET /review/queue` e `POST /review/{extraction_id}` | Fila de revisão e correção |
| `POST /ask` | Pergunta ao agente, com resposta e citações |
| `GET /metrics` | Métricas da seção 9.3 |

Requisitos: chave por cabeçalho `X-API-Key` nas rotas de escrita e de agente; validação Pydantic; erros claros sem traceback; testes de contrato com snapshot do OpenAPI.

---

## 12. Demo, automação e dataset

### 12.1 Demo (Streamlit)
- **Explorar:** busca de contratos, filtros e cartões com os campos principais.
- **Contrato:** PDF renderizado com os campos **destacados por cor** sobre a página, legenda com valor, confiança e trecho; divergências com o dado oficial em destaque.
- **Perguntar:** chat com o agente, com citações clicáveis que abrem a página certa.
- **Benchmark:** tabela e gráfico de acerto contra custo.
- **Operação:** custo, latência, fallback, revisão.
- **Revisão** (só local): fila de revisão humana.
- Versão pública em modo leitura, usando resultados pré-calculados, sem chamar o LLM por visitante (ou com limite diário bem baixo, se o Eduardo quiser).

### 12.2 Alerta semanal (n8n, Diferencial)
- Toda segunda-feira, o n8n chama a API e manda no Telegram os contratos que vencem nos próximos 30 e 60 dias, com link para a demo.
- Fluxo exportado em JSON, sem credenciais, com teste que verifica isso.

### 12.3 Dataset aberto (Diferencial)
- Publicar os campos extraídos (sem dados pessoais) em CSV e Parquet, no Hugging Face Datasets ou no Kaggle, com `docs/dataset-card.md`: fonte, recorte, método, métricas de qualidade, limitações e licença.
- Confirmar na Fase 0 as condições de uso dos dados do PNCP e registrar.

---

## 13. Fases, em ordem, com critério de pronto

### Fase 0: verificação e ambiente (o Eduardo faz, guiado)
1. Investigar a API do PNCP (seção 6.1) com chamadas de teste, sem baixar em volume, e registrar o que existe.
2. Chave do LLM e verificação do suporte a saída estruturada.
3. Instalar o Tesseract com o idioma português no Windows.
4. Instalar o Ollama e escolher um modelo que rode bem na máquina do Eduardo (medir a velocidade).
5. Docker Desktop funcionando; testar se o Phoenix roda (opcional).
6. Conta no Hugging Face (demo e dataset).
7. Registrar tudo em `docs/setup-verificacao.md`, incluindo o plano B se os PDFs não estiverem disponíveis.

**Pronto quando:** a rota de documentos está confirmada (ou o plano B está decidido em ADR), o LLM responde a uma chamada autorizada, o OCR e o Ollama funcionam.

### Fase 1: fundação e coleta
1. Estrutura, `pyproject.toml`, requirements, `.gitignore`, `.env.example`, LICENSE, CI.
2. `core/` (config, logs, erros, custos, mascaramento) com testes.
3. Banco, modelos e migração inicial.
4. Coletor do PNCP: fila, limite de taxa, retentativas, idempotência e retomada após queda; testes com `FakePNCP`.
5. Coleta do recorte definido; números reais anotados.

**Pronto quando:** o recorte está baixado de forma reproduzível e o coletor retoma de onde parou.

### Fase 2: leitura de documentos
1. Texto com coordenadas, detecção de escaneado e OCR.
2. Trechos com caixa delimitadora.
3. Estatísticas: páginas, porcentagem escaneada, tamanho médio.

**Pronto quando:** todos os documentos têm trechos com coordenadas e o OCR foi aplicado onde precisava.

### Fase 3: extração com LLM e validações (Essencial)
1. Esquema Pydantic e prompt v1.
2. Gateway mínimo (cache, retentativas, registro de custo).
3. Extração em lote **com autorização e estimativa de custo**.
4. Validações e confiança por campo.
5. Avaliação contra o dado oficial e análise manual de uma amostra das divergências.

**Pronto quando:** existe acerto por campo contra o dado oficial, com números reais e a análise das divergências.

### Fase 4: conjunto de referência e comparação de extratores (Avançado)
1. Guia de rótulos e tela de rotulagem na demo.
2. **O Eduardo anota cerca de 100 contratos.**
3. Extrator por regras e extrator local.
4. Benchmark completo e decisão de produção em ADR; model card da extração.

**Pronto quando:** `docs/benchmark.md` tem a tabela com números reais e a escolha justificada.

### Fase 5: busca e agente (Avançado)
1. Indexação, BM25, vetores, fusão e reranker.
2. Avaliação de recuperação (recall@k e MRR).
3. Ferramentas e laço do agente, com guardrails e verificação de citação.
4. Avaliação do agente e validação do juiz.

**Pronto quando:** as métricas de recuperação e do agente estão publicadas e todo caso de ataque é bloqueado ou tratado.

### Fase 6: LLMOps e API
1. Gateway completo: fallback, orçamento, limite de taxa.
2. Rastreamento (Phoenix ou painel próprio) e `GET /metrics`.
3. API completa com testes de contrato.
4. Regressão no CI.

**Pronto quando:** um teste mostra o fallback funcionando, o orçamento recusa chamadas ao estourar e o CI roda a regressão.

### Fase 7: demo e revisão humana
1. Telas da seção 12.1, com destaque no PDF.
2. Fila de revisão funcionando.
3. Publicação da demo em modo leitura.

**Pronto quando:** qualquer pessoa abre o link público e vê um contrato com os campos destacados.

### Fase 8: diferenciais
1. Servidor MCP e `docs/mcp.md`.
2. Teste de carga com Locust e resultado no relatório.
3. Red team do agente com resultado em `docs/seguranca.md`.
4. Relatório de inconsistências de cadastro (tom neutro).
5. Dataset aberto com data card.
6. Alerta semanal no n8n.

**Pronto quando:** o Claude Desktop usa o ContratoLens via MCP e o dataset está publicado.

### Fase 9: documentação e lançamento
1. README com: frase de efeito, GIF da demo, link da demo, **seção "Números" no topo** (acerto por campo, custo por mil documentos, recall@5, casos de ataque bloqueados, testes), arquitetura, como rodar do zero, decisões, limitações.
2. Design doc, runbook, postmortem simulado, relatório de custos, model cards e ADRs revisados.
3. ADRs mínimos:
   1. fonte de dados e plano B;
   2. `pdfplumber` + OCR seletivo;
   3. escolha do extrator de produção por qualidade e custo;
   4. confiança e revisão humana;
   5. busca híbrida com reranker;
   6. ferramentas com SQL parametrizado em vez de SQL livre;
   7. gateway com fallback e orçamento;
   8. MCP como interface para agentes;
   9. demo pública em modo leitura;
   10. conjunto de referência e uso (ou não) de apoio de IA na anotação.
4. `docs/roteiro-video.md` e `docs/post-linkedin.md`.
5. Checklist final (seção 15).

---

## 14. Vídeo e post

**Vídeo (2 a 3 minutos):**
1. O problema em uma frase e a arquitetura em uma imagem.
2. A demo: um contrato com os campos destacados no PDF e uma divergência com o cadastro.
3. Uma pergunta ao agente com a resposta citando a página.
4. O Claude Desktop usando o ContratoLens via MCP.
5. Uma tentativa de prompt injection dentro de um PDF sendo ignorada.
6. O benchmark (acerto contra custo) e o painel de operação.
7. Testes e CI verdes.

**Post no LinkedIn (`docs/post-linkedin.md`):**
- gancho com o número principal real (ex.: "Processei X mil contratos públicos com IA: Y% de acerto por campo a R$ Z por mil documentos");
- três decisões: comparar regras, LLM e modelo local pelo custo; citar a página em toda resposta; gateway com fallback e orçamento;
- imagem do benchmark e GIF da demo;
- links da demo, do repositório e do dataset.

---

## 15. Checklist final antes de publicar

- [ ] Clonar o repositório numa pasta nova e seguir o README do zero: funciona?
- [ ] `docker compose up` sobe API, banco, worker e demo.
- [ ] `pytest` passa e o CI está verde.
- [ ] Nenhum segredo no histórico (`git log -p | Select-String "AIza|sk-|gsk_|hf_"` vazio).
- [ ] Nenhum dado pessoal no dataset, na demo ou nos exemplos.
- [ ] Todo número do README, do site e do post reproduzido por script.
- [ ] Demo pública abrindo e sem chamar o LLM por visitante (ou com limite).
- [ ] Achados escritos em tom neutro.
- [ ] Design doc, runbook, postmortem, benchmark, relatório de custos, model cards, data card e ADRs no repositório.
- [ ] O Eduardo leu `docs/aprendizado.md` e consegue explicar cada decisão.

---

## 16. Riscos e planos B

| Risco | Plano B |
| --- | --- |
| A API não entrega os PDFs dos contratos | Usar outro tipo de documento do PNCP com metadado (editais, atas) ou outra fonte oficial; registrar em ADR |
| Limite de requisições baixo | Recorte menor, coleta em dias diferentes, retomada automática |
| Muitos PDFs escaneados e OCR ruim | Reportar os resultados separados; usar o LLM com imagem da página só se o custo couber |
| Cota do LLM esgota | Fallback de provedor, cache, extração só das páginas relevantes, regras primeiro |
| Modelo local lento demais | Avaliar numa amostra menor e documentar |
| Phoenix pesado demais | Painel próprio com `llm_calls` |
| Demo gratuita fica lenta | Pré-calcular as imagens das páginas e limitar o número de contratos na versão pública |
| O prazo aperta | Cortar na ordem: n8n, dataset aberto, teste de carga, modelo local, MCP. Nunca cortar a avaliação contra o dado oficial, a citação de página, os testes ou a documentação |

---

## 17. Perguntas prováveis em entrevistas (para o Eduardo se preparar)

1. **Como você mediu a qualidade da extração?** Comparei com o dado oficial do portal em todos os contratos, por campo, e com um conjunto de referência para as cláusulas.
2. **O dado oficial é sempre a verdade?** Não; analisei uma amostra das divergências e separei erro do extrator de inconsistência de cadastro.
3. **Por que não usar só o LLM?** O benchmark mostrou acerto, custo e latência de cada abordagem; a escolha veio dos números.
4. **Como o agente evita inventar?** Ferramentas com SQL parametrizado, citação obrigatória verificada por código e recusa quando não há dado.
5. **E se o provedor de LLM cair?** O gateway troca de provedor; se o orçamento estoura, a extração cai para regras e revisão humana. Está no runbook.
6. **Por que MCP?** Para que qualquer agente compatível use as ferramentas sem integração nova; é o padrão que empresas estão adotando.
7. **Como você tratou prompt injection em documentos?** Texto de documento é dado, não instrução; testei com PDFs maliciosos fictícios.
8. **O que faria com mais tempo?** Aditivos contratuais, comparação de preços por item, mais fontes e deploy com fila distribuída.

---

## 18. Primeira mensagem sugerida para o Claude Code

> Leia `CLAUDE.md` por inteiro. Faça esse projeto, começando pela **Fase 0**: me guie, passo a passo, para verificar a API do PNCP (principalmente se dá para baixar os PDFs dos contratos), criar a chave do LLM, instalar o Tesseract e o Ollama no Windows e conferir o Docker, um passo por vez, esperando eu confirmar cada um. Siga as regras da seção 2: não faça push, não leia nem imprima segredos e não gaste a cota do LLM sem me pedir. Ao terminar a Fase 0, registre tudo em `docs/setup-verificacao.md` e me mostre o plano da Fase 1.
