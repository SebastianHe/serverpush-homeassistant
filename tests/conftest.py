"""Home Assistant fixtures for the custom integration."""

import pytest


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Allow discovery of this repository's integration."""
