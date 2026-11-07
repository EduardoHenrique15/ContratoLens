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
