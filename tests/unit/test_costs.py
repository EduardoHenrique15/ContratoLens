from decimal import Decimal

import pytest

from contratolens.core.costs import ModelPrice, cost_brl, cost_per_thousand_docs

PRICE = ModelPrice("modelo-teste", Decimal("0.30"), Decimal("2.50"))


def test_cost_brl():
    # 1M de entrada (0,30 USD) + 100 mil de saída (0,25 USD) = 0,55 USD * 5,00 = 2,75 BRL
    assert cost_brl(1_000_000, 100_000, PRICE, Decimal("5.00")) == Decimal("2.7500")


def test_cost_rejects_negative_tokens():
    with pytest.raises(ValueError):
        cost_brl(-1, 0, PRICE, Decimal("5"))


def test_cost_per_thousand_docs():
    assert cost_per_thousand_docs(Decimal("12.34"), 500) == Decimal("24.68")
    with pytest.raises(ValueError):
        cost_per_thousand_docs(Decimal("1"), 0)
