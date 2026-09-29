"""
tests/conftest.py - Fast Headless Test Configuration
"""
from __future__ import annotations
import os
import pytest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"


@pytest.fixture(scope="session", autouse=True)
def enforce_headless_environment():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"


@pytest.fixture
def anyio_backend():
    return "asyncio"
