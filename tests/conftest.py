"""Fixtures compartilhadas: banco SQLite temporário, PNCP falso e cliente sem espera."""

import pytest
import respx
from tenacity import wait_none

from contratolens.db.base import Base
from contratolens.db.session import make_engine, make_session_factory
from contratolens.ingest.pncp_client import PNCPClient
from contratolens.ingest.rate_limit import MinIntervalLimiter
from tests.fakes.fake_pncp import API, CONSULTA, FakePNCP

PDF_BYTES = b"%PDF-1.4\n% contrato ficticio\n"


@pytest.fixture
def session_factory(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield make_session_factory(engine)
    engine.dispose()


@pytest.fixture
def fake_pncp():
    fake = FakePNCP()
    with respx.mock(assert_all_called=False) as router:
        fake.install(router)
        yield fake


@pytest.fixture
def client(fake_pncp):
    pncp = PNCPClient(
        consulta_base_url=CONSULTA,
        api_base_url=API,
        user_agent="contratolens-testes",
        limiter=MinIntervalLimiter(0),
        max_attempts=3,
        wait=wait_none(),
    )
    yield pncp
    pncp.close()
