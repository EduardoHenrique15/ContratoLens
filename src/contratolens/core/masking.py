"""Mascaramento de dados pessoais (CPF, e-mails e telefones) antes de enviar ao LLM ou publicar.

CNPJ de empresas e e-mails institucionais de órgãos públicos são dados públicos e não são
mascarados.
"""

import re

CPF_MASK = "***.***.***-**"
EMAIL_MASK = "[email removido]"
PHONE_MASK = "[telefone removido]"

_PUBLIC_EMAIL_SUFFIXES = (".gov.br", ".leg.br", ".jus.br", ".mp.br", ".def.br")

_CPF_FORMATTED = re.compile(r"(?<![\d./])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\d/])")
_CPF_DIGITS = re.compile(r"(?<![\d./-])\d{11}(?![\d/-])")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[-\s]?\d{4}(?!\d)")


def is_valid_cpf(digits: str) -> bool:
    """Confere os dígitos verificadores de um CPF com 11 dígitos."""
    if len(digits) != 11 or not digits.isdigit() or digits == digits[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(d) * w for d, w in zip(digits[:size], range(size + 1, 1, -1), strict=True))
        check = (total * 10) % 11 % 10
        if check != int(digits[size]):
            return False
    return True


def mask_cpf(text: str) -> str:
    """Mascara CPFs formatados e sequências de 11 dígitos que são CPFs válidos."""
    text = _CPF_FORMATTED.sub(CPF_MASK, text)
    return _CPF_DIGITS.sub(lambda m: CPF_MASK if is_valid_cpf(m.group()) else m.group(), text)


def mask_emails(text: str) -> str:
    """Mascara e-mails, exceto os de domínios públicos (.gov.br, .jus.br, ...)."""

    def _replace(match: re.Match[str]) -> str:
        email = match.group().lower()
        return match.group() if email.endswith(_PUBLIC_EMAIL_SUFFIXES) else EMAIL_MASK

    return _EMAIL.sub(_replace, text)


def mask_phones(text: str) -> str:
    """Mascara telefones brasileiros (fixos e celulares, com ou sem DDD e código do país)."""
    return _PHONE.sub(PHONE_MASK, text)


def mask_personal_data(text: str) -> str:
    """Aplica todos os mascaramentos. A ordem evita que um CPF seja lido como telefone."""
    return mask_phones(mask_emails(mask_cpf(text)))
