import pytest
from unittest.mock import patch, MagicMock, PropertyMock

@pytest.fixture(autouse=True)
def mock_gcs_credentials():
    """Auto-mock GCS credentials for CI environments without GCP auth."""
    mock_creds = MagicMock()
    mock_creds.universe_domain = "googleapis.com"
    mock_creds.token = "fake-token"
    with patch("google.auth.default", return_value=(mock_creds, "test-project")):
        yield mock_creds
