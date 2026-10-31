"""
tests/conftest.py - Fast Headless Test Configuration
"""
from __future__ import annotations
import hashlib
import importlib.util
import os
import pytest

# Skip collecting the benchmark module when the optional research dependency is missing,
# so plain `pytest -q` works on a dev machine without mir_eval.
collect_ignore = []
if importlib.util.find_spec("mir_eval") is None:
    collect_ignore.append("test_benchmark_engine.py")

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"


@pytest.fixture(scope="session", autouse=True)
def enforce_headless_environment():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"


_REAL_APP_CONFIG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "config", "app_config.json")
)


def _sha256_of(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def _app_config_isolation(tmp_path_factory):
    """Redirect AppConfigStore writes to a temp file and fail if the real config changes."""
    from core.AppConfigStore import AppConfigStore

    tmp_cfg = str(tmp_path_factory.mktemp("app_config") / "app_config.json")
    before = _sha256_of(_REAL_APP_CONFIG)
    original = AppConfigStore._resolve_app_config_path
    AppConfigStore._resolve_app_config_path = lambda self: tmp_cfg
    try:
        yield
    finally:
        AppConfigStore._resolve_app_config_path = original
    assert _sha256_of(_REAL_APP_CONFIG) == before, (
        "config/app_config.json was modified during the test session"
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"
