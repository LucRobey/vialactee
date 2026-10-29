"""
tests/conftest.py - Fast Headless Test Configuration
"""
from __future__ import annotations
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


@pytest.fixture
def anyio_backend():
    return "asyncio"
