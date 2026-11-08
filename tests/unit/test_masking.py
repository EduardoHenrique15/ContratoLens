import pytest

from contratolens.core.masking import (
    CPF_MASK,
    EMAIL_MASK,
    PHONE_MASK,
    is_valid_cpf,
    mask_cpf,
    mask_emails,
    mask_personal_data,
    mask_phones,
)

VALID_CPF = "52998224725"  # CPF de exemplo com dígitos verificadores válidos


def test_is_valid_cpf():
    assert is_valid_cpf(VALID_CPF)
    assert not is_valid_cpf("52998224724")
    assert not is_valid_cpf("11111111111")
    assert not is_valid_cpf("123")


def test_masks_formatted_cpf():
    assert mask_cpf("CPF 529.982.247-25, residente") == f"CPF {CPF_MASK}, residente"


def test_masks_only_valid_unformatted_cpf():
    assert mask_cpf(f"cpf {VALID_CPF}") == f"cpf {CPF_MASK}"
    assert mask_cpf("protocolo 12345678901") == "protocolo 12345678901"


@pytest.mark.parametrize(
    "text",
    ["CNPJ 11.222.333/0001-81", "CNPJ 11222333000181", "valor R$ 71.240,90", "Processo 1752/2026"],
)
def test_keeps_public_and_non_personal_numbers(text):
    assert mask_personal_data(text) == text


def test_masks_personal_email_but_keeps_public_domains():
    text = "contato: joao.silva@gmail.com ou licitacao@saosalvador.to.gov.br"
    assert mask_emails(text) == f"contato: {EMAIL_MASK} ou licitacao@saosalvador.to.gov.br"


@pytest.mark.parametrize(
    "phone", ["(63) 99999-1234", "63 3333-4444", "+55 63 99999-1234", "6399991234"]
)
def test_masks_phones(phone):
    assert mask_phones(f"tel {phone}.") == f"tel {PHONE_MASK}."


def test_does_not_mask_dates_as_phones():
    assert (
        mask_phones("vigência de 14/08/2026 a 14/08/2027") == "vigência de 14/08/2026 a 14/08/2027"
    )


def test_mask_personal_data_combines_all():
    text = "Fiscal: CPF 529.982.247-25, fone (63) 99999-1234, e-mail ana@hotmail.com"
    masked = mask_personal_data(text)
    assert "529.982" not in masked and "99999" not in masked and "ana@" not in masked
    assert CPF_MASK in masked and PHONE_MASK in masked and EMAIL_MASK in masked
