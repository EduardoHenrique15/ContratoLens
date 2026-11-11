# ADR 0007: leitura de PDF com pdfplumber e OCR seletivo por página

- Status: aceita
- Data: 2026-11-11

## Contexto

O projeto precisa citar a página e destacar o trecho de cada campo extraído em cima do PDF. Para isso, o
texto precisa vir com a posição de cada palavra. Os documentos misturam PDFs com texto nativo e PDFs
escaneados (o PDF de teste da Fase 0 era escaneado). A coleta trouxe 1.026 arquivos, com tamanho mediano
de 0,10 MB, o que sugere muitos PDFs com texto nativo, e 11 arquivos que não são PDF.

## Decisão

1. **`pdfplumber`** extrai as palavras com a caixa delimitadora (`x0`, `top`, `x1`, `bottom`, em pontos do
   PDF, origem no topo). Licença MIT.
2. **OCR só nas páginas que precisam** (Tesseract, idioma `por`, 300 dpi via `pypdfium2`). Regras:
   imagem cobrindo a maior parte da página com pouco texto (scan com carimbo de assinatura); pouco texto
   e alguma imagem; ou página sem texto nenhum mas com "tinta" ao renderizar em baixa resolução (imagem
   que o `pdfplumber` não detectou). Página curta sem imagem fica com o texto nativo.
3. As coordenadas do OCR são convertidas de pixels para pontos do PDF, no mesmo sistema do texto nativo.
4. **Armazenamento:** cada página guarda todas as palavras com coordenadas (tabela `pages`, JSON
   compacto), para o destaque exato e para a validação "o trecho citado existe na página". Os trechos
   (`chunks`: parágrafos ou cláusulas, até 1.500 caracteres) guardam a caixa que envolve suas palavras.
   Um novo trecho começa num espaço vertical grande ou numa linha que começa com CLÁUSULA, SUBCLÁUSULA
   ou PARÁGRAFO.
5. **Paralelismo local:** um processo por núcleo (`ProcessPoolExecutor`), cada Tesseract limitado a uma
   thread (`OMP_THREAD_LIMIT=1`). Só o processo principal escreve no banco. Aqui o paralelismo é
   adequado, ao contrário da coleta, porque não pesa sobre nenhum serviço externo.
6. **Formato pelo conteúdo, não pela extensão:** os primeiros bytes decidem (PDF, JPEG, PNG, TIFF, DOCX,
   ODT, DOC antigo, HTML). Imagens passam por OCR; formatos não tratados ficam registrados como
   `unsupported`, com o tipo detectado.
7. **Idempotência:** documento lido com a mesma versão do leitor (`READER_VERSION`) é pulado; reprocessar
   substitui páginas e trechos, sem duplicar.

## Consequências

- O OCR a 300 dpi leva cerca de 3,35 s por página por núcleo (Fase 0). Com 4 processos, o tempo cai a
  cerca de um quarto.
- Páginas giradas e tabelas complexas podem gerar ordem de leitura imperfeita; vai para as limitações.
- O JSON de palavras ocupa espaço no banco (estimativa: dezenas de MB para 1.000 documentos).

## Atualização (2026-11-11): primeira leitura real

- Um contrato real trouxe o caractere nulo (`\x00`) no texto extraído, que o PostgreSQL recusa. O
  leitor passou a remover caracteres de controle e invisíveis (`clean_text`) do texto nativo e do OCR.
- A falha de gravação de um documento derrubava o lote, e o encerramento esperava a fila inteira
  terminar (parecia travado). Agora a falha vira `processing_status = error` com a mensagem, o lote
  continua, e um Ctrl+C cancela na hora os documentos que ainda não começaram.
- Avisos do `pdfminer` sobre PDFs malformados ("Cannot begin marked-content...") foram silenciados no
  log: não afetam a extração.
