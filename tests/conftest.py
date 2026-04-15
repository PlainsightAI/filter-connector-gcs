import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_gcs_credentials():
    """Auto-mock GCS credentials for CI environments without GCP auth."""
    mock_creds = MagicMock()
    with patch("google.auth.default", return_value=(mock_creds, "test-project")):
        yield mock_creds
