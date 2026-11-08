# ADR 0005: desenho do coletor do PNCP

- Status: aceita
- Data: 2026-11-08

## Contexto

A coleta faz milhares de chamadas a uma API pública, numa máquina doméstica que pode desligar ou perder
a conexão. Ela precisa respeitar a fonte, não baixar nada duas vezes e retomar de onde parou.

## Decisão

1. **Fila no próprio banco** (`ingest_jobs`), sem serviço extra (Redis, Celery). Cada tarefa tem chave
   única, então reenfileirar o mesmo período não duplica nada.
2. **Dois tipos de tarefa:** `list_window` (uma página de listagem por vez, com a próxima página salva no
   payload) e `contract_files` (lista os arquivos de um contrato e baixa os do tipo "Contrato").
3. **Arquivos têm prioridade** sobre a listagem, para os downloads avançarem junto e a coleta poder parar
   ao atingir a meta (`--meta`), deixando o resto na fila.
4. **Retomada:** ao iniciar, tarefas que ficaram `running` (queda no meio) voltam para `pending`.
5. **Duas camadas de nova tentativa:** o cliente repete erros transitórios com espera crescente
   (`tenacity`); se ainda falhar, a tarefa volta para a fila até `max_attempts` e depois vira `failed`,
   com o erro registrado.
6. **Respeito à fonte:** intervalo mínimo entre chamadas (`PNCP_MIN_INTERVAL_SECONDS`, padrão 1 s) e
   `User-Agent` genérico, sem e-mail.
7. **Download atômico:** grava em `.part` e renomeia; guarda SHA-256 e tamanho para idempotência.
8. **Minimização de dados:** o CPF de fornecedor pessoa física é mascarado antes de ir para o banco,
   inclusive no JSON bruto. O projeto não precisa dele.

## Consequências

- Um único processo de coleta por vez (a fila não trava linhas entre processos concorrentes). Suficiente
  para o volume do projeto; um worker distribuído fica como melhoria futura.
- O filtro por UF é feito no cliente, porque a listagem de contratos não filtra por UF. Por isso, a coleta
  lê páginas de todo o país para achar os contratos das UFs escolhidas.
