"""
Pytest configuration for Music Royalty Settlement Engine tests.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_test_state():
    """Reset any global state between tests."""
    yield
