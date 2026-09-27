"""Legacy offline tests remain a contract suite, not evidence for live model quality."""
import pytest

@pytest.fixture(autouse=True)
def legacy_engine_by_default(monkeypatch):
    monkeypatch.setenv('USE_VERIFIED_AI','false')
