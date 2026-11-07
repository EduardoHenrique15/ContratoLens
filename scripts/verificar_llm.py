"""Verificação da Fase 0: uma única chamada ao LLM com saída estruturada.

Lê a chave de GEMINI_API_KEY no arquivo .env (sem imprimir o valor), envia um trecho
fictício de contrato e valida a resposta com Pydantic. Custo: 1 chamada, poucas
centenas de tokens.

Uso (PowerShell): .\\.venv\\Scripts\\python.exe scripts\\verificar_llm.py
"""

import os
import sys
import time

from dotenv import load_dotenv
from openai import NotFoundError, OpenAI
from pydantic import BaseModel, ValidationError

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-2.5-flash"

SAMPLE_TEXT = (
    "CONTRATO Nº 12/2026. CONTRATANTE: Município de Exemplo, CNPJ 11.222.333/0001-81. "
    "CONTRATADA: Empresa Fictícia Ltda, CNPJ 11.444.777/0001-61. O valor total do "
    "contrato é de R$ 71.240,90 (setenta e um mil, duzentos e quarenta reais e noventa "
    "centavos). A vigência será de 14/08/2026 a 14/08/2027. Os preços serão reajustados "
    "anualmente pelo IPCA."
)


class ContractCheck(BaseModel):
    """Esquema mínimo para testar a saída estruturada."""

    contratada: str
    cnpj_contratada: str
    valor_total: float
    vigencia_inicio: str
    vigencia_fim: str
    indice_reajuste: str | None


def main() -> int:
    """Faz a chamada de teste e mostra modelo, latência, tokens e campos extraídos."""
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        print("GEMINI_API_KEY não encontrada no .env.")
        return 1
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    client = OpenAI(api_key=os.environ["GEMINI_API_KEY"], base_url=BASE_URL)

    start = time.perf_counter()
    try:
        response = _call(client, model)
    except NotFoundError:
        print(f"Modelo '{model}' não encontrado (404). Modelos disponíveis:")
        names = sorted(m.id for m in client.models.list())
        print("\n".join(names))
        print("Escolha um e defina GEMINI_MODEL no .env.")
        return 1
    latency = time.perf_counter() - start

    content = response.choices[0].message.content or ""
    return _report(response, content, latency)


def _call(client: OpenAI, model: str):
    """Envia o trecho fictício pedindo saída no esquema ContractCheck."""
    return client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Extraia os campos do contrato. Datas em AAAA-MM-DD. "
                "Use null quando o campo não existir no texto.",
            },
            {"role": "user", "content": SAMPLE_TEXT},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "contract_check",
                "schema": ContractCheck.model_json_schema(),
            },
        },
    )


def _report(response, content: str, latency: float) -> int:
    """Valida a resposta com Pydantic e mostra modelo, latência e tokens."""
    try:
        parsed = ContractCheck.model_validate_json(content)
    except ValidationError as exc:
        print("Resposta não passou na validação Pydantic:")
        print(content)
        print(exc)
        return 1

    usage = response.usage
    print(f"Modelo: {response.model}")
    print(f"Latência: {latency:.2f} s")
    if usage:
        print(f"Tokens: entrada={usage.prompt_tokens} saída={usage.completion_tokens}")
    print("Campos validados pelo Pydantic:")
    print(parsed.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
