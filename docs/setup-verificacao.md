# Verificação do ambiente e da fonte de dados (Fase 0)

> Registro do que foi testado na Fase 0, com data e resultado. Testes feitos pelo Eduardo no PowerShell (Windows),
> pois a sessão do Claude Code roda na nuvem e não alcança `pncp.gov.br`.

## 1. API do PNCP

Data dos testes: 2026-11-07. Cliente identificado de forma genérica: `User-Agent: contratolens-pesquisa/0.1`.
Nenhuma autenticação foi necessária nas rotas de consulta abaixo.

### 1.1 Listagem de contratos (API de consulta)

`GET https://pncp.gov.br/api/consulta/v1/contratos`

| Parâmetro | Formato | Observação |
| --- | --- | --- |
| `dataInicial` | `AAAAMMDD` | Obrigatório |
| `dataFinal` | `AAAAMMDD` | Obrigatório |
| `pagina` | inteiro, começa em 1 | Obrigatório |
| `tamanhoPagina` | inteiro | Máximo 500 (com 501 a API devolve HTTP 400) |

Resultado do teste (`dataInicial=20261001`, `dataFinal=20261007`, `tamanhoPagina=10`):
`totalRegistros = 42137`, `totalPaginas = 4214`. Paginação vem em `totalRegistros`, `totalPaginas`, `numeroPagina`
e os itens em `data`.

### 1.2 Campos estruturados de cada contrato (gabarito oficial)

| Campo do projeto | Campo do PNCP |
| --- | --- |
| Identificador | `numeroControlePNCP` (ex.: `37344371000109-2-000115/2026`) |
| Chave para arquivos | `orgaoEntidade.cnpj` + `anoContrato` + `sequencialContrato` |
| Contratante | `orgaoEntidade.razaoSocial`, `unidadeOrgao.nomeUnidade`, `unidadeOrgao.ufSigla`, `orgaoEntidade.esferaId` |
| Contratada | `nomeRazaoSocialFornecedor` |
| CNPJ da contratada | `niFornecedor` (é CPF quando `tipoPessoa = "PF"`: mascarar) |
| Objeto | `objetoContrato` |
| Valor | `valorGlobal`, `valorInicial`, `valorParcela`, `numeroParcelas`, `valorAcumulado` |
| Datas | `dataAssinatura`, `dataVigenciaInicio`, `dataVigenciaFim` |
| Tipo | `tipoContrato.nome` (ex.: "Contrato (termo inicial)"), `categoriaProcesso.nome` |
| Controle | `dataPublicacaoPncp`, `dataAtualizacao`, `numeroRetificacao` |

Observação: o PowerShell 5.1 mostrou acentos quebrados (`AquisiÃ§Ã£o`) porque decodifica a resposta com a
codificação errada. O conteúdo vem em UTF-8; o cliente `httpx` do projeto decodifica corretamente.

### 1.3 Arquivos (PDF) de cada contrato: CONFIRMADO

Listar: `GET https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos`

Resposta com `url`, `sequencialDocumento`, `titulo`, `tipoDocumentoNome` (ex.: "Contrato"), `dataPublicacaoPncp`.

Baixar: `GET https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos/{sequencialDocumento}`

Teste com o contrato `37344371000109-2-000115/2026`: `Content-Type: application/octet-stream`,
`Content-Disposition: attachment; filename="...pdf"`, 4.662.567 bytes, começa com `%PDF-`.

**Conclusão:** a rota de documentos existe e é pública. O plano B (editais/atas) não é necessário.

### 1.4 Cobertura em amostra pequena (10 primeiros registros da página 1)

| Resultado | Registros |
| --- | --- |
| 1 arquivo do tipo "Contrato" | 4 |
| Só "Nota de Empenho" | 4 |
| "Nota de Empenho" + 2 "Outros Documentos" | 2 |

Todos os 10 registros tinham pelo menos 1 arquivo, mas só 4 tinham o instrumento contratual. Os 6 restantes são
do mesmo órgão (`07954480000179`), que publica notas de empenho como "contrato" no PNCP.

**Implicação para a Fase 1:** a coleta precisa filtrar pelos arquivos com `tipoDocumentoNome = "Contrato"`
(e olhar `tipoContrato.nome`), senão o recorte se enche de notas de empenho, que não têm cláusulas.
A amostra é pequena e concentrada; a cobertura real será medida na coleta.

### 1.5 Tipo do PDF

O PDF de teste (`37344371000109-2-000115/2026`, 4,6 MB) é **escaneado**: não há texto selecionável.
Isso indica que o OCR (Tesseract) será caminho principal para parte relevante da base, não exceção.
A fração de escaneados será medida na Fase 2, e os resultados da avaliação serão separados por tipo de PDF.

Observação técnica: no PowerShell 5.1, `Invoke-RestMethod` devolve uma lista JSON como um objeto só;
é preciso desenrolar com `ForEach-Object { $_ }` para contar os itens.

## 2. LLM (Gemini via endpoint compatível com o SDK `openai`)

Data do teste: 2026-11-07. Script: `scripts/verificar_llm.py` (uma única chamada autorizada pelo Eduardo).

- Provedor: Google Gemini (camada gratuita do Google AI Studio), chave em `GEMINI_API_KEY` no `.env`.
- Endpoint: `https://generativelanguage.googleapis.com/v1beta/openai/`, SDK `openai` 3.46.0.
- O modelo `gemini-2.5-flash` aparece na listagem, mas devolveu HTTP 404 para a chave nova
  (provavelmente não está mais liberado para projetos novos). O script agora lista os modelos disponíveis no 404.
- Modelo escolhido para a verificação: `gemini-3.8-flash` (o Flash estável mais recente, sem `preview`),
  configurável por `GEMINI_MODEL` no `.env`. A escolha final (Flash ou Flash-Lite) sai do benchmark da Fase 4.

Resultado: saída estruturada por `response_format` do tipo `json_schema` funcionou e passou na validação Pydantic.

| Métrica | Valor |
| --- | --- |
| Latência (1 chamada, inclui abertura da conexão) | 8,04 s |
| Tokens de entrada / saída | 190 / 91 |
| Campos corretos no trecho fictício | 6 de 6 (contratada, CNPJ, valor, vigência início e fim, índice IPCA) |
| Custo | R$ 0,00 (camada gratuita) |

Pendência: registrar os preços por token do modelo escolhido (camada paga) antes da estimativa de custo da Fase 3.
Na camada gratuita, o Google pode usar o conteúdo enviado para melhorar seus produtos; o projeto só envia
texto de contratos públicos, com CPF, e-mails e telefones pessoais mascarados.

## 3. OCR (Tesseract)

Data do teste: 2026-11-07. Script: `scripts/verificar_ocr.py` (local, sem serviço externo).

- Tesseract 5.5.3 (instalador UB Mannheim) em `C:\Program Files\Tesseract-OCR`, no PATH do usuário.
- Idiomas instalados: `eng`, `osd`, `por`.
- Bibliotecas Python: `pypdfium2` 5.15.0 (renderiza a página) e `pytesseract` 0.3.13.

Teste na página 1 do contrato `37344371000109-2-000115/2026` (PDF escaneado, 23 páginas):

| Métrica | Valor |
| --- | --- |
| Texto nativo na página 1 | 10 caracteres (confirma que é escaneado) |
| Tempo de OCR (300 dpi, 1 página) | 3,35 s |
| Palavras reconhecidas | 323 |
| Confiança média do Tesseract | 94,6 |

O trecho reconhecido estava legível e correto ("INSTRUMENTO CONTRATUAL Nº 52/2026 ... PREGÃO ELETRÔNICO Nº 005/2026").

**Implicação de custo de tempo:** a 3,35 s por página, um contrato de 23 páginas leva cerca de 77 s de OCR.
Para milhares de documentos escaneados, a Fase 2 precisa de OCR em paralelo (vários processos), cache do
resultado por hash do arquivo e, se necessário, OCR primeiro só nas páginas mais relevantes.

**Observação de qualidade de dados (a verificar):** no PDF, o número do instrumento é "52/2026"; no cadastro
do portal, `numeroContratoEmpenho` é "53". Pode ser numeração diferente entre sistemas ou erro de digitação em
qualquer um dos lados. É o tipo de inconsistência de cadastro que o projeto vai medir, sem tirar conclusões.

## 4. Modelo local (Ollama)

Data do teste: 2026-11-07. Ollama instalado pelo instalador oficial do Windows, usado só localmente (sem conta).

Máquina do Eduardo: Intel Core i7-1165G7 (4 núcleos), 8 GB de RAM, Intel Iris Xe + NVIDIA GeForce MX330 (2 GB).
Com 8 GB de RAM e 2 GB de VRAM, só cabem modelos de cerca de 3 bilhões de parâmetros (quantizados), rodando
majoritariamente na CPU.

Modelo escolhido: `qwen2.5:3b` (cerca de 1,9 GB). Teste com `ollama run qwen2.5:3b --verbose`:

| Métrica | Valor |
| --- | --- |
| Carregamento do modelo (só na primeira chamada) | 38,4 s |
| Leitura do prompt | 82 tokens a 15,3 tokens/s |
| Geração | 103 tokens a 10,8 tokens/s |
| Duração total | 53,4 s |

A resposta trouxe valor e vigência corretos, em JSON, mas com texto extra em volta e datas no formato
DD/MM/AAAA. Na extração real, o projeto usa o modo JSON com esquema do Ollama e validação Pydantic.

**Estimativa para a extração local:** um prompt com as páginas relevantes de um contrato tem cerca de 4 mil
tokens. A 15 tokens/s, só a leitura leva cerca de 4,5 minutos por documento, mais cerca de 30 s de geração.
Isso dá cerca de 8 horas para 100 contratos.

**Decisão:** o extrator local será avaliado só no conjunto de referência (cerca de 100 contratos), não na base
inteira. Esse é o plano B previsto na seção 16 ("modelo local lento demais: avaliar numa amostra menor").
O resultado e o custo de máquina entram no benchmark.

## 5. Docker Desktop

Data do teste: 2026-11-07. Docker Desktop 4.90.0, Engine 29.7.2 (contexto `desktop-linux`).
`docker run --rm hello-world` executou com sucesso.

Atenção: com 8 GB de RAM, Docker (PostgreSQL), Ollama e VS Code não devem rodar cargas pesadas ao mesmo tempo.

## 6. Hugging Face

Conta criada em 2026-11-07: usuário `EduardoHenrique15` (igual ao GitHub). Será usada para a demo (Spaces)
e para o dataset aberto. O token de acesso só será criado na Fase 7 e ficará no `.env`.

## 7. Condições de uso dos dados do PNCP

- O PNCP declara que adota o formato de dados abertos e observa a Lei de Acesso à Informação (Lei nº 12.527/2011),
  e que o acesso aos dados de contratações publicados é público e universal, sem login
  ([perguntas e respostas do PNCP](https://www.gov.br/pncp/pt-br/pncp/perguntas-e-respostas)).
- Não foi encontrada uma licença explícita (por exemplo, CC-BY) para os dados nem termos de uso específicos da API.
- **Pendência para a Fase 8 (dataset aberto):** procurar de novo a licença no portal; enquanto não houver,
  o dataset cita a fonte (PNCP), a data da coleta, a base legal (LAI) e não contém dados pessoais.

## 8. Rastreamento (Phoenix)

Não testado. Com 8 GB de RAM, um contêiner a mais disputaria memória com PostgreSQL e Ollama.
Proposta: painel próprio na demo a partir da tabela `llm_calls` (alternativa prevista na seção 9.2).
Ver `docs/decisoes/0003-rastreamento-sem-phoenix.md`.

## Resumo da Fase 0

| Item | Resultado |
| --- | --- |
| Rota de documentos (PDF) | Confirmada e pública; plano B não necessário |
| LLM | `gemini-3.8-flash` respondeu com saída estruturada válida (1 chamada, R$ 0,00) |
| OCR | Tesseract 5.5.3 com `por`, confiança média 94,6 em PDF escaneado |
| Ollama | `qwen2.5:3b` funciona, 15 tokens/s de leitura e 10,8 tokens/s de geração |
| Docker | Docker Desktop 4.90.0 funcionando |
| Hugging Face | Conta `EduardoHenrique15` criada |
