# ADR 0006: recorte da coleta (1.000 contratos de outubro de 2026, todo o país)

- Status: aceita e executada (coleta concluída em 2026-11-11)
- Data: 2026-11-08

## Contexto

A especificação mira entre 3 mil e 10 mil contratos com PDF. O levantamento de 2026-11-08
(`scripts/levantar_recorte.py`, semana de 1 a 7 de outubro de 2026, semente 42) mediu:

| Medida | Valor |
| --- | --- |
| Registros na semana | 42.137 (85 páginas de 500) |
| UFs com mais registros | SC 11.080, SP 9.942, MG 3.118, GO 2.897, RS 2.723 |
| Esferas | municipal 30.286, estadual 5.994, federal 5.244 |
| Tipos | Empenho 16.837, Contrato (termo inicial) 14.195, Outros 10.956 |
| Amostra de 40 contratos | 20 com PDF de contrato, 5 só com outros documentos, 15 com erro |
| Cobertura entre os que responderam | 20 de 25 (80%) |
| Tempo da rota de arquivos | mediana 51 s, p95 331 s (inclui novas tentativas) |

A rota de arquivos do PNCP respondeu com muitos `503` e timeouts: está sobrecarregada. O tipo de
contrato não prevê a existência do PDF (até "Empenho" teve 8 de 12 com contrato), então filtrar por
tipo não reduz chamadas inúteis.

## Decisão

1. **Meta de cerca de 1.000 contratos com PDF**, abaixo da faixa da especificação. Com cerca de 70
   contratos por hora, 3 mil levariam mais de 50 horas de coleta, e o OCR da Fase 2 (cerca de 77 s
   por documento escaneado) levaria mais de 60 horas na máquina do Eduardo.
2. **Período: outubro de 2026, todas as UFs e esferas**, sem filtro por tipo.
3. **Ordem pseudoaleatória e reprodutível** (`--semente 42`): o coletor lista o mês inteiro primeiro e
   baixa os contratos em ordem de um hash do id com a semente. Assim a amostra não fica concentrada
   nos primeiros dias nem nos órgãos que publicam primeiro.
4. **Sem paralelismo** contra a API: o servidor já está sobrecarregado; a coleta roda em várias
   noites e retoma de onde parou. Tarefas que falharam podem voltar à fila com `--refazer-falhas`.
5. Os metadados de **todos** os contratos do mês ficam no banco (gabarito oficial e base para o agente),
   mesmo os sem PDF baixado.

## Consequências

- A avaliação contra o dado oficial (Fase 3) terá cerca de 1.000 documentos, não milhares. O número
  real entra no README; aumentar a base depois é só rodar a coleta com uma meta maior.
- A cobertura de 80% vem de uma amostra pequena (25 respostas); a cobertura real será medida na coleta.
- Os 37% de erro na amostra mostram que a disponibilidade do PNCP é um risco operacional; vai para o
  runbook.

## Resultado (2026-11-11)

Números de `scripts/estatisticas_coleta.py` (`eval/results/coleta_20261111.json`):

- 174.956 contratos de outubro de 2026 no banco; 1.000 com PDF de contrato baixado (meta atingida).
- Cobertura de PDF entre os consultados: 80,4% (1.000 de 1.244), igual à estimativa da amostra (80%).
- Falhas após todas as tentativas: 271 de 1.515 consultas (17,9%), menos que os 37% da amostra.
- 1.026 documentos, 0,96 GB; tamanho mediano de 0,10 MB, bem abaixo dos 4,6 MB do PDF escaneado da
  Fase 0. A estimativa de disco (4,5 GB) ficou 4,7 vezes acima do real.
- Distribuição: SC tem 32,8% dos baixados contra 26,3% dos registros na semana do levantamento; SP tem
  15,4% contra 23,6%. A amostra segue o volume do PNCP, mas não é perfeitamente proporcional por UF
  (a cobertura de PDF e as falhas variam entre órgãos). Isso entra nas limitações.
