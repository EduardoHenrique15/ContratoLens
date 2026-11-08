"""Cálculo de custo de chamadas de LLM em reais.

Os preços não ficam fixos no código: vêm da documentação oficial do provedor e são passados
explicitamente, para que todo custo publicado tenha fonte e data.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class ModelPrice:
    """Preço de um modelo em dólares por milhão de tokens."""

    model: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal


def cost_brl(
    input_tokens: int, output_tokens: int, price: ModelPrice, usd_to_brl: Decimal
) -> Decimal:
    """Custo em reais (4 casas decimais) de uma chamada com os tokens informados."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("A quantidade de tokens não pode ser negativa.")
    usd = (
        Decimal(input_tokens) * price.input_usd_per_million
        + Decimal(output_tokens) * price.output_usd_per_million
    ) / Decimal(1_000_000)
    return (usd * usd_to_brl).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def cost_per_thousand_docs(total_cost_brl: Decimal, documents: int) -> Decimal:
    """Custo em reais por mil documentos."""
    if documents <= 0:
        raise ValueError("A quantidade de documentos precisa ser positiva.")
    return (total_cost_brl * Decimal(1000) / Decimal(documents)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
