# ADR 0002: extrator local avaliado só no conjunto de referência

- Status: aceita
- Data: 2026-11-07

## Contexto

A máquina do Eduardo tem 8 GB de RAM e GPU NVIDIA MX330 com 2 GB. O modelo `qwen2.5:3b` no Ollama leu o prompt a
15,3 tokens/s e gerou a 10,8 tokens/s. Um contrato tem cerca de 4 mil tokens nas páginas relevantes, o que leva
cerca de 5 minutos por documento.

## Decisão

Usar `qwen2.5:3b` como modelo local e rodar o extrator local só no conjunto de referência (cerca de 100 contratos,
cerca de 8 horas), não na base inteira. É o plano B da seção 16 para "modelo local lento demais".

## Consequências

- O benchmark compara os três extratores no mesmo conjunto de referência; regras e LLM também rodam na base inteira.
- O custo de máquina do extrator local é estimado pelo tempo medido, não é zero.
- Se o tempo for inviável, testar `gemma3:1b` e documentar a perda de qualidade.
