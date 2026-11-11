# Aprendizado: o que foi feito e por quê

> Explicações em português simples, fase por fase, para eu (Eduardo) conseguir explicar cada decisão em entrevistas.

## Fase 0: verificação e ambiente

**Objetivo.** Antes de escrever código, confirmar que os dados existem e que as ferramentas funcionam na minha
máquina. Um engenheiro de IA começa testando as premissas: se a fonte não tiver os PDFs, o projeto inteiro muda.

**1. A API do PNCP entrega os PDFs.** A listagem de contratos traz os metadados oficiais (valor, datas,
fornecedor, CNPJ, objeto), que vão servir de gabarito para medir a extração. Uma segunda rota lista e baixa os
arquivos de cada contrato, sem login. Por isso não precisei do plano B.

**2. Nem todo "contrato" tem um contrato.** Em 10 registros, 6 tinham só nota de empenho (o documento que
reserva o dinheiro no orçamento, sem cláusulas). Decisão: baixar só arquivos do tipo "Contrato". Lição: olhar os
dados de verdade antes de planejar evita encher a base de documentos inúteis.

**3. Os PDFs podem ser escaneados.** O PDF testado era uma imagem, sem texto selecionável. O OCR (Tesseract)
leu a página com confiança média de 94,6, mas levou 3,35 s por página. Para milhares de documentos, isso vira
horas: vou precisar de OCR em paralelo e cache por hash do arquivo.

**4. O LLM responde em formato estruturado.** Usei o Gemini pelo endpoint compatível com o SDK da OpenAI, o que
permite trocar de provedor só mudando a configuração. Pedi a saída num esquema JSON e validei com Pydantic:
6 de 6 campos certos num texto de teste. O primeiro modelo testado deu erro 404 (não liberado para chaves
novas), então o script passou a listar os modelos disponíveis e o modelo virou configuração (`GEMINI_MODEL`).

**5. O modelo local é lento na minha máquina.** Com 8 GB de RAM e uma GPU de 2 GB, o `qwen2.5:3b` lê cerca de
15 tokens por segundo: uns 5 minutos por contrato. Decisão: comparar o modelo local só nos cerca de 100 contratos
do conjunto de referência. Saber dizer "medi e decidi pelo número" é mais forte do que "achei que seria lento".

**6. Segredos fora do git desde o início.** O `.gitignore` foi criado antes de a chave existir, e a chave fica
só no `.env`. Ela nunca foi colada no chat nem impressa por nenhum script.

**7. Achado inesperado.** No PDF, o contrato é o nº 52/2026; no portal, o número cadastrado é 53. Ainda não sei
qual lado está certo. É exatamente o tipo de "inconsistência de cadastro a verificar" que o projeto vai medir,
sem acusar ninguém.

**Perguntas que posso responder em entrevista:**
- Por que testar a API antes de programar? Porque a existência dos PDFs era a premissa mais arriscada do projeto.
- Por que filtrar por tipo de documento? Porque nota de empenho não tem cláusulas e distorceria a avaliação.
- Por que o modelo local só numa amostra? Porque medi a velocidade: a base inteira levaria semanas na minha máquina.

## Fase 1: fundação e coleta

**Objetivo.** Montar a base do projeto (configuração, banco, testes, CI) e baixar um recorte real de
contratos de forma que dê para repetir e retomar.

**1. Uma fila no próprio banco.** Cada coisa a fazer (listar uma página, baixar os arquivos de um
contrato) vira uma linha na tabela `ingest_jobs`, com chave única. Se o computador desligar, ao reiniciar
o coletor devolve as tarefas pela metade para a fila e continua. Isso aconteceu de verdade: a coleta caiu
por um bug e retomou da página certa depois da correção.

**2. Respeitar a fonte.** O PNCP devolveu `429 Too Many Requests` com 1 chamada por segundo. Subi o
intervalo para 2 s, passei a respeitar o cabeçalho `Retry-After` e não usei paralelismo, porque a rota de
arquivos já estava sobrecarregada (erros 503 e timeouts). Ser educado com a API pública faz parte do
trabalho.

**3. Medir antes de decidir.** O levantamento só com metadados mostrou que a rota de arquivos levava, na
mediana, 51 s por contrato. Com esse número, a meta caiu de 3 mil para 1.000 contratos (ADR 0006): mais
que isso levaria dias de coleta e de OCR na minha máquina. A cobertura medida na amostra (80%) bateu com a
da coleta real (80,4%).

**4. Amostra sem viés de ordem.** Em vez de baixar os primeiros contratos da listagem (que concentrariam
os primeiros dias do mês), o coletor lista o mês inteiro e baixa numa ordem embaralhada por um hash do id
com semente fixa. A mesma semente sempre dá a mesma amostra: é reproduzível.

**5. Dado real quebra suposição.** Um fornecedor estrangeiro veio com o "CNPJ" igual a
`ESTRANGEIRO_GLOBAL_LIFE`, maior que a coluna do banco, e a coleta caiu. Os testes não pegaram porque o
SQLite não confere o tamanho de texto. Correção: colunas de texto livre viraram `TEXT`, cada registro é
gravado separado (um registro ruim é pulado e anotado no log) e o CI passou a rodar os testes também no
PostgreSQL. Lição: testar no mesmo banco da produção.

**6. Privacidade desde a coleta.** Quando o fornecedor é pessoa física, o CPF é mascarado antes de ir para
o banco, inclusive no JSON bruto. O projeto não precisa desse dado, então não guarda.

**7. Números de verdade, com script.** Todos os números da coleta saem de `scripts/estatisticas_coleta.py`:
174.956 contratos de outubro de 2026 no banco, 1.000 com PDF, cobertura de 80,4%, 17,9% de consultas com
falha e 0,96 GB de PDFs (mediana de 0,10 MB por arquivo, o que sugere muitos PDFs com texto nativo).

**Perguntas que posso responder em entrevista:**
- Como a coleta sobrevive a uma queda? Fila no banco com chave única, tarefas `running` voltam para
  `pending` ao reiniciar, e download atômico (arquivo `.part` renomeado no fim).
- Por que só 1.000 contratos? Porque medi a velocidade da fonte e do OCR; a decisão e os números estão na
  ADR 0006, e aumentar a base é só rodar a coleta com uma meta maior.
- A amostra é representativa? Segue o volume do PNCP (municípios e SC dominam), mas não é perfeitamente
  proporcional por UF; isso está documentado como limitação.
