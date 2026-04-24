import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from dcs_log_viewer.main import app
from dcs_log_viewer.parser import LEVELS

client = TestClient(app)

def test_index_page():
    """Verify that the root path serves the HTML SPA shell."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "DCS Log Viewer" in response.text

def test_get_levels():
    """Verify that the /api/levels endpoint returns correctly normalized log levels."""
    response = client.get("/api/levels")
    assert response.status_code == 200
    data = response.json()
    assert "levels" in data
    # Normalised: WARNING -> WARN, ERROR_ONCE -> ERROR
    assert "WARN" in data["levels"]
    assert "ERROR" in data["levels"]
    assert "WARNING" not in data["levels"]

@patch("dcs_log_viewer.ws.get_config")
def test_get_config(mock_get_config):
    """Verify that /api/config correctly retrieves the current application state."""
    mock_get_config.return_value = {"theme": "dark", "log_path": "test.log"}
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {"theme": "dark", "log_path": "test.log"}

@patch("dcs_log_viewer.ws.get_config")
@patch("dcs_log_viewer.routes.save_config")
def test_post_config(mock_save, mock_get):
    """Verify that POSTing to /api/config updates the state and persists it to disk."""
    mock_get.return_value = {"theme": "dark"}
    response = client.post("/api/config", json={"theme": "light", "new_key": 123})
    assert response.status_code == 200
    # Should update and return
    data = response.json()
    assert data["theme"] == "light"
    assert data["new_key"] == 123
    mock_save.assert_called_once()

@patch("dcs_log_viewer.routes.asyncio.to_thread")
def test_browse_file(mock_to_thread):
    """Verify that the /api/browse endpoint correctly proxies the native file-picker."""
    # Mocking the async call that opens the dialog
    mock_to_thread.return_value = "C:/mocked/dcs.log"
    response = client.get("/api/browse")
    assert response.status_code == 200
    assert response.json() == {"path": "C:/mocked/dcs.log"}
