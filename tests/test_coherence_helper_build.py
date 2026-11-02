"""Authoritative-check smoke tests for the Coherence Policy HTML helper."""
import pytest

from tools import build_coherence_helper as helper


@pytest.mark.parametrize("profile", helper.PROFILES)
def test_shipped_policies_pass_authoritative_check(profile):
    assert helper.check(profile) is True

