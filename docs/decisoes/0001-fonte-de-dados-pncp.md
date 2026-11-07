# ADR 0001: fonte de dados e filtro de documentos do PNCP

- Status: aceita
- Data: 2026-11-07

## Contexto

A especificação usa o PNCP como fonte e prevê um plano B caso a API não entregue os PDFs dos contratos.
Na Fase 0 foram testadas a listagem de contratos da API de consulta e as rotas de arquivos da API do PNCP.

## Decisão

1. Usar a API pública do PNCP: `GET /api/consulta/v1/contratos` para os metadados (máximo de 500 itens por
   página) e `GET /api/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos` para listar e baixar os PDFs.
2. Baixar só os arquivos com `tipoDocumentoNome = "Contrato"`. Numa amostra de 10 registros, 6 tinham apenas
   notas de empenho (sem cláusulas), todas do mesmo órgão.
3. O plano B (editais e atas) não é necessário.

## Consequências

- O recorte de 3 mil a 10 mil contratos com PDF é viável: há cerca de 42 mil registros por semana.
- A fração de registros com contrato precisa ser medida na coleta e publicada.
- O PDF de teste era escaneado: o OCR é caminho principal, não exceção (ver ADR sobre leitura de PDF na Fase 2).
