import pytest
import os
from dcs_log_web.main import _lifespan, main
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_app_lifespan():
    """Verify the startup/shutdown logic directly without TestClient overhead."""
    mock_app = MagicMock()
    with patch("dcs_log_web.main.load_config") as mock_load:
        mock_load.return_value = {"theme": "custom"}
        with patch("dcs_log_web.main.ws_state.set_config") as mock_set:
            # Manually trigger the async context manager
            async with _lifespan(mock_app):
                mock_load.assert_called_once()
                mock_set.assert_called_once_with({"theme": "custom"})

def test_main_cli_defaults():
    """Verify that main() uses default host/port when environment is empty."""
    with patch("dcs_log_web.main.uvicorn.run") as mock_run:
        with patch("dcs_log_web.main.os.environ", {}):
            with patch("builtins.print"): # Suppress print
                main()
                mock_run.assert_called_once_with(
                    "dcs_log_web.main:app",
                    host="127.0.0.1",
                    port=8420,
                    log_level="info",
                    reload=False
                )

def test_main_cli_custom_env():
    """Verify that main() respects DCS_LOG_PORT and other env vars."""
    custom_env = {
        "DCS_LOG_PORT": "9000",
        "DCS_LOG_HOST": "0.0.0.0",
        "DCS_LOG_LEVEL": "debug"
    }
    with patch("dcs_log_web.main.uvicorn.run") as mock_run:
        with patch("dcs_log_web.main.os.environ", custom_env):
            with patch("builtins.print"):
                main()
                mock_run.assert_called_once_with(
                    "dcs_log_web.main:app",
                    host="0.0.0.0",
                    port=9000,
                    log_level="debug",
                    reload=False
                )
