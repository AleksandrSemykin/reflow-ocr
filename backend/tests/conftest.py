from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from reflow_ocr.app import create_app
from reflow_ocr.core import config
from reflow_ocr.services import reset_session_store


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    config.settings.data_dir = tmp_path
    tmp_path.mkdir(parents=True, exist_ok=True)
    reset_session_store()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    reset_session_store()
