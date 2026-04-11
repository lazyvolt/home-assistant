"""Root conftest: enable HA custom integration loading for all tests."""
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom_components/ discovery for every test."""
    return
